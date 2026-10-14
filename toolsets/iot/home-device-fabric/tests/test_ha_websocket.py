"""Proposed REQ-024 tests; literal wire/state expectations, no live HA."""

import asyncio
import builtins
import copy
import importlib
import inspect
import io
import json
import logging
import os
import pickle
import ssl
import subprocess
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.ha_websocket_async
TOKEN = "fictional-websocket-credential-7249"
URL = "http://fixture.invalid:8123"


def runtime():
    return importlib.import_module("home_device_fabric.ha_websocket")


def configuration(*, url=URL, timeout=10000, attempts=3):
    from home_device_fabric.ha_configuration import HAConfiguration

    return HAConfiguration({"schema_version": 1, "base_url": url,
                            "request_timeout_ms": timeout,
                            "reconnect_initial_delay_ms": 10,
                            "reconnect_max_delay_ms": 25,
                            "reconnect_max_attempts": attempts}, access_token=TOKEN)


class Socket:
    def __init__(self, messages=('{"type":"auth_required"}', '{"type":"auth_ok"}'),
                 *, close=None):
        self.messages = list(messages)
        self.sent = []
        self.closed = 0
        self.aborted = 0
        self.close_hook = close
        self.transport = SimpleNamespace(abort=self.abort)
        self.waiting = asyncio.Event()

    def abort(self):
        self.aborted += 1

    async def recv(self):
        if self.messages:
            value = self.messages.pop(0)
            if isinstance(value, BaseException):
                raise value
            return value
        self.waiting.set()
        await asyncio.Future()

    async def send(self, text):
        self.sent.append(json.loads(text))

    async def close(self):
        self.closed += 1
        if self.close_hook:
            await self.close_hook()


def fake(monkeypatch, sockets):
    mod = runtime()
    state = SimpleNamespace(attempts=0, delays=[], transitions=[])
    publish = mod.HAWebSocketClient._publish

    def record(client, *args, **kwargs):
        publish(client, *args, **kwargs)
        state.transitions.append(client.health().to_dict())

    async def connect(config):
        state.attempts += 1
        value = sockets.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value

    async def sleep(delay):
        state.delays.append(delay)
        await asyncio.sleep(0)

    monkeypatch.setattr(mod, "_connect", connect)
    monkeypatch.setattr(mod, "_sleep", sleep)
    monkeypatch.setattr(mod.HAWebSocketClient, "_publish", record)
    return state


async def wait_state(client, state):
    async with asyncio.timeout(3):
        while client.health().state != state:
            await asyncio.sleep(0)


@pytest.mark.tc024_01
def test_api_and_authentication(monkeypatch):
    async def scenario():
        mod = runtime()
        assert mod.__all__ == ["HAWebSocketClient", "HAConnectionHealth"]
        socket = Socket()
        state = fake(monkeypatch, [socket])
        client = mod.HAWebSocketClient(configuration())
        initial = client.health()
        assert initial.to_dict() == {"state": "disconnected", "reason": None,
                                     "reconnect_attempt": 0, "sequence": 0}
        assert state.attempts == 0
        run = asyncio.create_task(client.run())
        await wait_state(client, "connected")
        assert socket.sent == [{"type": "auth", "access_token": TOKEN}]
        assert [h["state"] for h in state.transitions] == [
            "connecting", "authenticating", "connected"]
        assert initial.state == "disconnected" and not run.done()
        assert {name for name, member in inspect.getmembers(mod.HAWebSocketClient)
                if not name.startswith("_") and callable(member)} == {"run", "aclose", "health"}
        with pytest.raises(RuntimeError, match="^client_started$"):
            await client.run()
        await client.aclose()
        await run
        assert client.health().state == "closed" and socket.closed == 1
        with pytest.raises(RuntimeError, match="^client_closed$"):
            await client.run()
    asyncio.run(scenario())


@pytest.mark.parametrize("invalid", [None, {}, "http://fake.invalid", 1, True])
@pytest.mark.tc024_01
def test_invalid_configuration(invalid):
    with pytest.raises(TypeError, match="^invalid_configuration$"):
        runtime().HAWebSocketClient(invalid)


@pytest.mark.tc024_01
@pytest.mark.ha_websocket_pure
def test_construction_has_no_ambient_io(monkeypatch, offline):
    mod, config = runtime(), configuration()
    calls = []

    def denied(*args, **kwargs):
        calls.append(1)
        raise AssertionError("construction attempted I/O")

    class Environment(dict):
        __getitem__ = get = __iter__ = denied

    with monkeypatch.context() as patch:
        for owner, name in ((builtins, "open"), (io, "open"), (os, "open"),
                            (Path, "open"), (asyncio, "new_event_loop")):
            patch.setattr(owner, name, denied)
        patch.setattr(os, "environ", Environment())
        client = mod.HAWebSocketClient(config)
        assert client.health().state == "disconnected"
    assert calls == [] and offline == []


@pytest.mark.parametrize("flap", [False, True])
@pytest.mark.tc024_02
def test_finite_backoff_and_flapping(monkeypatch, flap):
    async def scenario():
        sockets = [Socket(messages=['{"type":"auth_required"}', '{"type":"auth_ok"}',
                                    OSError(TOKEN)]) for _ in range(4)] if flap else []
        state = fake(monkeypatch, list(sockets) if flap else [OSError(TOKEN)] * 4)
        client = runtime().HAWebSocketClient(configuration())
        await client.run()
        assert state.attempts == 4 and state.delays == [0.01, 0.02, 0.025]
        assert client.health().state == "failed"
        assert client.health().reason == "reconnect_exhausted"
        assert client.health().reconnect_attempt == 3
        sequences = [h["sequence"] for h in state.transitions]
        assert all(new > previous for previous, new in zip([0, *sequences], sequences))
        assert [x["reconnect_attempt"] for x in state.transitions
                if x["state"] == "connecting"] == [0, 1, 2, 3]
        assert all(s.closed == 1 for s in sockets)
        assert TOKEN not in repr(state.transitions)
        with pytest.raises(RuntimeError, match="client_started"):
            await client.run()
        await client.aclose()
        assert client.health().state == "closed"
        assert client.health().reason == "reconnect_exhausted"
    asyncio.run(scenario())


@pytest.mark.parametrize("messages", [
    ['{"type":"auth_invalid","message":"' + TOKEN + '"}'],
    ['{"type":"auth_required"}', '{"type":"auth_invalid","message":"' + TOKEN + '"}'],
], ids=["auth-invalid-first", "auth-invalid-after-token"])
@pytest.mark.tc024_03
def test_auth_rejection_stops(monkeypatch, messages):
    async def scenario():
        socket = Socket(messages)
        state = fake(monkeypatch, [socket])
        client = runtime().HAWebSocketClient(configuration())
        await client.run()
        assert client.health().state == "auth_failed"
        assert client.health().reason == "auth_failed"
        assert state.attempts == 1 and not state.delays and socket.closed == 1
        assert TOKEN not in repr(client.health())
        await client.aclose()
    asyncio.run(scenario())


@pytest.mark.parametrize("message", [
    b'{"type":"auth_required"}', "[]", "null", "{}", "true", "not-json",
    '{"type":4}', '{"type":"auth_ok"}',
    '{"type":"auth_required","type":"auth_required"}',
    '{"type":"auth_required","ignored":NaN}',
    '{"type":"auth_required","ignored":Infinity}',
    '{"type":"auth_required","ignored":{"x":1,"x":2}}',
    '{"type":"auth_required","ignored":"' + "x" * 65536 + '"}',
    "[" * 2000,
], ids=["binary", "array", "null", "empty", "bool", "bad-json", "numeric-type",
        "early-ok", "duplicate", "nan", "infinity", "nested-duplicate", "oversize", "deep"])
@pytest.mark.tc024_03
def test_invalid_initial_messages(monkeypatch, message):
    async def scenario():
        socket = Socket([message])
        state = fake(monkeypatch, [socket])
        client = runtime().HAWebSocketClient(configuration())
        await client.run()
        assert client.health().state == "failed"
        assert client.health().reason == "protocol_error"
        assert not socket.sent and not state.delays and socket.closed == 1
    asyncio.run(scenario())


@pytest.mark.parametrize("messages", [
    ['{"type":"auth_required"}', '{"type":"auth_required"}'],
    ['{"type":"auth_required"}', '{}'],
    ['{"type":"auth_required"}', '{"type":"auth_ok"}', '{"type":"event"}'],
])
@pytest.mark.tc024_03
def test_out_of_order_and_unsolicited_messages(monkeypatch, messages):
    async def scenario():
        socket = Socket(messages)
        state = fake(monkeypatch, [socket])
        client = runtime().HAWebSocketClient(configuration())
        await client.run()
        assert client.health().reason == "protocol_error"
        assert not state.delays and socket.closed == 1
    asyncio.run(scenario())


@pytest.mark.parametrize("phase", ["connect", "auth", "connected", "backoff"])
@pytest.mark.tc024_04
def test_shutdown_all_phases(monkeypatch, phase):
    async def scenario():
        socket = Socket([] if phase == "auth" else (
            ['{"type":"auth_required"}', '{"type":"auth_ok"}']))
        state = fake(monkeypatch, [OSError(TOKEN)] if phase == "backoff" else [socket])
        entered = asyncio.Event()
        if phase in ("connect", "backoff"):
            async def block(*args):
                entered.set()
                await asyncio.Future()
            monkeypatch.setattr(runtime(), "_connect" if phase == "connect" else "_sleep", block)
        client = runtime().HAWebSocketClient(configuration())
        run = asyncio.create_task(client.run())
        if phase in ("connect", "backoff"):
            await asyncio.wait_for(entered.wait(), 3)
        else:
            await asyncio.wait_for(socket.waiting.wait(), 3)
        await asyncio.gather(client.aclose(), client.aclose(), client.aclose())
        await run
        assert client.health().state == "closed"
        assert socket.closed == (1 if phase in ("auth", "connected") else 0)
        terminal = [x["state"] for x in state.transitions]
        assert terminal[-1] == "closed"
        assert "connected" not in terminal[terminal.index("closed") + 1:]
    asyncio.run(scenario())


@pytest.mark.tc024_04
def test_cancel_run_repeatedly_drains_cleanup(monkeypatch):
    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()
        async def close():
            entered.set()
            await release.wait()
        socket = Socket(close=close)
        fake(monkeypatch, [socket])
        client = runtime().HAWebSocketClient(configuration())
        run = asyncio.create_task(client.run())
        await wait_state(client, "connected")
        run.cancel()
        await entered.wait()
        run.cancel()
        await asyncio.sleep(0)
        assert not run.done()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await run
        assert socket.closed == 1
        assert client.health().state == "disconnected"
        assert client.health().reason == "cancelled"
        await client.aclose()
    asyncio.run(scenario())


@pytest.mark.tc024_04
def test_cancellation_before_worker_starts(monkeypatch):
    async def scenario():
        state = fake(monkeypatch, [])
        client = runtime().HAWebSocketClient(configuration())
        running = asyncio.create_task(client.run())
        await asyncio.sleep(0)
        running.cancel()
        with pytest.raises(asyncio.CancelledError):
            await running
        assert client.health().state == "disconnected"
        assert client.health().reason == "cancelled"
        assert state.attempts <= 1
        await client.aclose()
    asyncio.run(scenario())


@pytest.mark.tc024_04
def test_cancel_close_waiter_does_not_cancel_close(monkeypatch):
    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()
        async def close():
            entered.set()
            await release.wait()
        socket = Socket(close=close)
        fake(monkeypatch, [socket])
        client = runtime().HAWebSocketClient(configuration())
        run = asyncio.create_task(client.run())
        await wait_state(client, "connected")
        closer = asyncio.create_task(client.aclose())
        await entered.wait()
        closer.cancel()
        with pytest.raises(asyncio.CancelledError):
            await closer
        assert client.health().state == "closed" and not run.done()
        release.set()
        await client.aclose()
        await run
        assert socket.closed == 1
    asyncio.run(scenario())


@pytest.mark.parametrize("failure", ["timeout", "exception"])
@pytest.mark.tc024_04
def test_cleanup_abort(monkeypatch, failure):
    async def scenario():
        async def close():
            if failure == "exception":
                raise OSError(TOKEN)
            await asyncio.Future()
        monkeypatch.setattr(runtime(), "_CLEANUP_SECONDS", 0.01)
        socket = Socket(close=close)
        fake(monkeypatch, [socket])
        client = runtime().HAWebSocketClient(configuration())
        run = asyncio.create_task(client.run())
        await wait_state(client, "connected")
        await asyncio.wait_for(client.aclose(), 2)
        await run
        assert socket.aborted == 1 and client.health().state == "closed"
    asyncio.run(scenario())


@pytest.mark.parametrize("phase", ["connect", "auth"])
@pytest.mark.tc024_04
def test_auth_budget_is_bounded(monkeypatch, phase):
    async def scenario():
        sockets = [Socket([]), Socket([])]
        state = fake(monkeypatch, list(sockets))
        if phase == "connect":
            async def block(*args):
                state.attempts += 1
                await asyncio.Future()
            monkeypatch.setattr(runtime(), "_connect", block)
        client = runtime().HAWebSocketClient(configuration(timeout=10, attempts=1))
        await asyncio.wait_for(client.run(), 2)
        assert client.health().reason == "reconnect_exhausted"
        assert state.attempts == 2 and state.delays == [0.01]
        assert any(t["reason"] == "timeout" for t in state.transitions)
        if phase == "auth":
            assert all(s.closed == 1 for s in sockets)
        else:
            assert all(s.closed == 0 and not s.sent for s in sockets)
    asyncio.run(scenario())


@pytest.mark.tc024_04
def test_cross_loop_and_close_before_run():
    client = runtime().HAWebSocketClient(configuration())
    async def first():
        await client.aclose()
        await client.aclose()
        with pytest.raises(RuntimeError, match="client_closed"):
            await client.run()
    asyncio.run(first())
    for method in (client.aclose, client.run):
        with pytest.raises(RuntimeError, match="wrong_event_loop"):
            asyncio.run(method())


@pytest.mark.tc024_05
def test_health_and_diagnostic_privacy():
    mod = runtime()
    client = mod.HAWebSocketClient(configuration())
    snapshot = client.health()
    exported = snapshot.to_dict()
    exported["state"] = TOKEN
    assert snapshot.state == "disconnected"
    with pytest.raises(FrozenInstanceError):
        snapshot.state = TOKEN
    for operation in (pickle.dumps, copy.copy, copy.deepcopy, lambda c: c.__getstate__()):
        with pytest.raises(TypeError, match="client_serialization_refused"):
            operation(client)
    assert repr(client) == str(client) == "HAWebSocketClient(<redacted>)"
    with pytest.raises(RuntimeError, match="client_initialized"):
        client.__init__(configuration())
    for values in ({"state": TOKEN}, {"reason": TOKEN}, {"sequence": True},
                   {"sequence": -1}, {"reconnect_attempt": 33}, {"reason": []}):
        with pytest.raises(ValueError, match="invalid_health"):
            mod.HAConnectionHealth(**values)


@pytest.mark.tc024_05
@pytest.mark.ha_websocket_wire
def test_loopback_wire_and_remote_close(monkeypatch, caplog):
    captured = []
    class Sink(logging.Handler):
        def emit(self, record):
            captured.append(record.getMessage())

    sink = Sink()
    logger = runtime()._WIRE_LOGGER
    original_level = logger.level
    logger.addHandler(sink)
    logger.setLevel(logging.DEBUG)
    async def scenario():
        from websockets.asyncio.server import serve
        requests, auths = [], []
        async def handler(ws):
            requests.append(ws.request)
            await ws.send('{"type":"auth_required","ha_version":"fixture"}')
            auths.append(json.loads(await ws.recv()))
            await ws.send('{"type":"auth_ok"}')
            await ws.close(reason=TOKEN)
        async def instant(delay):
            await asyncio.sleep(0)
        monkeypatch.setattr(runtime(), "_sleep", instant)
        async with serve(handler, "127.0.0.1", 0, compression=None) as server:
            port = server.sockets[0].getsockname()[1]
            client = runtime().HAWebSocketClient(configuration(
                url=f"http://127.0.0.1:{port}", attempts=1))
            # Bad proxy must not divert a real numeric-loopback connection.
            monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:1")
            monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
            monkeypatch.setenv("NO_PROXY", "")
            await asyncio.wait_for(client.run(), 3)
            assert client.health().reason == "reconnect_exhausted"
            assert auths == [{"type": "auth", "access_token": TOKEN}] * 2
            assert all(r.path == "/api/websocket" for r in requests)
            assert all("Authorization" not in r.headers and "User-Agent" not in r.headers
                       and "Sec-WebSocket-Extensions" not in r.headers for r in requests)
            await client.aclose()
        # Server owns its own logger; check only the client logger boundary.
        assert not [r for r in caplog.records if r.name == "websockets.client"]
        assert captured == []
    try:
        with caplog.at_level(logging.DEBUG):
            asyncio.run(scenario())
        # Sensitivity probe on the actual isolated logger, without any token:
        # prove the direct handler would catch a regression enabling DEBUG.
        logger.disabled = False
        logger.debug("logging-probe")
        assert captured == ["logging-probe"]
    finally:
        logger.disabled = True
        logger.setLevel(original_level)
        logger.removeHandler(sink)


@pytest.mark.parametrize("status,reason", [(301, "protocol_error"), (302, "protocol_error"),
                                           (401, "auth_failed"), (403, "auth_failed"),
                                           (500, "protocol_error")])
@pytest.mark.tc024_05
@pytest.mark.ha_websocket_wire
def test_loopback_http_rejection_and_redirect(monkeypatch, status, reason):
    async def scenario():
        from websockets.asyncio.server import serve
        seen = []
        async def process(connection, request):
            seen.append(request.path)
            response = connection.respond(status, TOKEN)
            response.headers["Location"] = "http://127.0.0.1:1/redirect"
            return response
        async def handler(ws):
            raise AssertionError("rejected handshake upgraded")
        async with serve(handler, "127.0.0.1", 0, process_request=process) as server:
            port = server.sockets[0].getsockname()[1]
            client = runtime().HAWebSocketClient(configuration(url=f"http://127.0.0.1:{port}"))
            await asyncio.wait_for(client.run(), 3)
            assert seen == ["/api/websocket"]
            assert client.health().reason == reason
            assert TOKEN not in repr(client.health())
            await client.aclose()
    asyncio.run(scenario())


@pytest.mark.tc024_05
def test_transport_options_and_scheme(monkeypatch):
    async def scenario():
        calls = []
        class Connector:
            def __init__(self, uri, **options):
                calls.append((uri, options))
            def __await__(self):
                async def value():
                    return Socket()
                return value().__await__()
        context = object()
        monkeypatch.setattr(runtime(), "_NoRedirectConnect", Connector)
        monkeypatch.setattr(runtime(), "_tls_context", lambda: context)
        for url in ("http://EXAMPLE.INVALID:08123/", "https://EXAMPLE.INVALID:00443/"):
            socket = await runtime()._connect(configuration(url=url))
            await socket.close()
        assert calls[0][0] == "ws://example.invalid:08123/api/websocket"
        assert calls[1][0] == "wss://example.invalid:00443/api/websocket"
        for _, options in calls:
            assert options["proxy"] is None and options["compression"] is None
            assert options["max_size"] == 65536 and options["max_queue"] == 4
            assert options["close_timeout"] == 1
            assert options["ping_interval"] == options["ping_timeout"] == 20
            assert options["logger"].disabled and not options["logger"].propagate
        assert calls[1][1]["ssl"] is context and calls[0][1]["ssl"] is None
    asyncio.run(scenario())


@pytest.mark.tc024_05
@pytest.mark.ha_websocket_wire
@pytest.mark.ha_websocket_tls_fixture
def test_real_tls_rejects_untrusted_even_with_ambient_override(tmp_path, monkeypatch):
    key, cert = tmp_path / "key.pem", tmp_path / "cert.pem"
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                    "-keyout", str(key), "-out", str(cert), "-days", "1",
                    "-subj", "/CN=localhost", "-addext", "subjectAltName=IP:127.0.0.1"],
                   check=True, capture_output=True, timeout=20)
    monkeypatch.setenv("SSL_CERT_FILE", str(cert))
    monkeypatch.setenv("SSL_CERT_DIR", str(tmp_path))
    context = runtime()._tls_context()
    assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED

    async def scenario():
        from websockets.asyncio.server import serve
        calls = []
        async def handler(ws):
            calls.append(1)
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(cert, key)
        async def instant(delay):
            await asyncio.sleep(0)
        monkeypatch.setattr(runtime(), "_sleep", instant)
        async with serve(handler, "127.0.0.1", 0, ssl=tls) as server:
            port = server.sockets[0].getsockname()[1]
            client = runtime().HAWebSocketClient(configuration(
                url=f"https://127.0.0.1:{port}", attempts=1))
            await asyncio.wait_for(client.run(), 5)
            assert client.health().reason == "reconnect_exhausted"
            assert not calls
            await client.aclose()
    asyncio.run(scenario())


@pytest.mark.tc024_05
@pytest.mark.ha_websocket_wire
def test_real_stalled_handshake_times_out(monkeypatch):
    async def scenario():
        requests, handlers = [], set()
        async def handler(reader, writer):
            task = asyncio.current_task()
            handlers.add(task)
            try:
                requests.append(await reader.read(4096))
                await reader.read()
            finally:
                writer.close()
                await writer.wait_closed()
                handlers.remove(task)
        async def instant(delay):
            await asyncio.sleep(0)
        monkeypatch.setattr(runtime(), "_sleep", instant)
        server = await asyncio.start_server(handler, "127.0.0.1", 0)
        async with server:
            port = server.sockets[0].getsockname()[1]
            client = runtime().HAWebSocketClient(configuration(
                url=f"http://127.0.0.1:{port}", timeout=50, attempts=1))
            await asyncio.wait_for(client.run(), 3)
            assert client.health().reason == "reconnect_exhausted"
            assert len(requests) == 2
            assert all(b"GET /api/websocket HTTP/1.1" in r for r in requests)
            assert all(TOKEN.encode() not in r for r in requests)
            await client.aclose()
        if handlers:
            await asyncio.wait_for(asyncio.gather(*list(handlers)), 2)
    asyncio.run(scenario())


@pytest.mark.tc024_04
def test_deadline_check_before_connected(monkeypatch):
    async def scenario():
        sockets = [Socket(), Socket()]
        state = fake(monkeypatch, list(sockets))
        base = asyncio.get_running_loop().time()
        times = iter([base, base + 1, base, base + 1])
        monkeypatch.setattr(runtime(), "_clock", lambda: next(times))
        client = runtime().HAWebSocketClient(configuration(timeout=100, attempts=1))
        await client.run()
        assert client.health().reason == "reconnect_exhausted"
        assert "connected" not in [h["state"] for h in state.transitions]
        assert all(s.closed == 1 for s in sockets)
    asyncio.run(scenario())


@pytest.mark.parametrize("phase", ["recv", "send", "close"])
@pytest.mark.tc024_04
def test_baseexception_still_closes_owned_socket(monkeypatch, phase):
    class ControlledExit(BaseException):
        pass

    async def scenario():
        socket = Socket([ControlledExit()] if phase == "recv" else [
            '{"type":"auth_required"}', '{"type":"unexpected"}'])
        if phase == "send":
            async def send(text):
                raise ControlledExit()
            socket.send = send
        if phase == "close":
            async def close():
                raise ControlledExit()
            socket.close_hook = close
        fake(monkeypatch, [socket])
        client = runtime().HAWebSocketClient(configuration())
        with pytest.raises(ControlledExit):
            await client.run()
        assert socket.closed == 1
        assert client.health().reason == "internal_error"
        await asyncio.gather(client.aclose(), client.aclose(), client.aclose())
        await client.aclose()
        assert client.health().state == "closed"
        assert client.health().reason == "internal_error"
        assert socket.closed == 1
    asyncio.run(scenario())


@pytest.mark.tc024_03
def test_unclassified_dependency_exception_is_finite(monkeypatch):
    async def scenario():
        state = fake(monkeypatch, [RuntimeError(TOKEN + URL)])
        client = runtime().HAWebSocketClient(configuration())
        await client.run()
        assert client.health().reason == "internal_error"
        assert state.attempts == 1 and not state.delays
        assert TOKEN not in repr(client.health()) + repr(client)
    asyncio.run(scenario())
