"""Literal proposed REQ-023 expectations, plus real loopback HTTP/TLS effects."""

import asyncio
import contextlib
import copy
import importlib
import json
import logging
import pickle
import socket
import ssl
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.ha_rest_boundary
TOKEN = "fictional-REST-credential-marker-7391"
URL = "http://fixture.invalid"


def runtime():
    return importlib.import_module("home_device_fabric.ha_rest")


def config(url=URL, timeout=10000):
    from home_device_fabric.ha_configuration import HAConfiguration

    return HAConfiguration({"schema_version": 1, "base_url": url,
                            "request_timeout_ms": timeout}, access_token=TOKEN)


def run(coroutine):
    return asyncio.run(coroutine)


def assert_error(error, code, correlation="call-1", status=None):
    assert type(error) is runtime().HARestError
    assert error.to_dict() == {"code": code, "correlation_id": correlation, "http_status": status}
    assert error.args == (code,) and str(error) == code
    assert error.__cause__ is None and error.__context__ is None
    assert TOKEN not in repr(error) + str(error) + repr(vars(error))
    assert URL not in repr(error) + str(error) + repr(vars(error))


def fake(monkeypatch, *, status=200, body=b'{"version":"2025.1.0"}',
         headers=None, chunks=None, before=None, close=None, send_error=None):
    import httpx

    state = SimpleNamespace(requests=[], clients=[], streams=[], body_reads=0)

    class Stream(httpx.AsyncByteStream):
        def __init__(self):
            self.closed = 0
            state.streams.append(self)

        async def __aiter__(self):
            state.body_reads += 1
            for chunk in chunks if chunks is not None else [body]:
                yield chunk

        async def aclose(self):
            try:
                if close:
                    await close()
            finally:
                self.closed += 1

    class Client:
        def __init__(self):
            self.closed = 0
            state.clients.append(self)

        async def send(self, request):
            state.requests.append(request)
            if before:
                await before()
            if send_error:
                raise send_error(request)
            return httpx.Response(status, headers=headers or {"Content-Type": "application/json"},
                                  stream=Stream(), request=request)

        async def aclose(self):
            self.closed += 1

    monkeypatch.setattr(runtime(), "_make_client", Client)
    return state


@contextlib.contextmanager
def server(*, status=200, body=b'{"version":"2025.1.0"}', headers=None,
           delay=0, trickle=False, tls=None):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append((self.command, self.path, dict(self.headers)))
            if delay:
                time.sleep(delay)
            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                for key, value in (headers or {}).items():
                    self.send_header(key, value)
                self.end_headers()
                for chunk in (list(body) if trickle else [body]):
                    self.wfile.write(bytes([chunk]) if trickle else chunk)
                    self.wfile.flush()
                    if trickle:
                        time.sleep(0.015)
            except OSError:
                pass  # Expected peer close on deadline/cancellation.

        def log_message(self, *args):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    # Drain request workers before the next test reinstates ambient-effect
    # denial; ThreadingHTTPServer otherwise leaves daemon handlers running.
    httpd.daemon_threads = False
    httpd.block_on_close = True
    if tls is not None:
        httpd.socket = tls.wrap_socket(httpd.socket, server_side=True)
    worker = threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.01},
                              daemon=True)
    worker.start()
    try:
        yield f'{"https" if tls else "http"}://127.0.0.1:{httpd.server_port}', requests
    finally:
        httpd.shutdown()
        httpd.server_close()
        worker.join(timeout=2)
        assert not worker.is_alive()


@pytest.mark.tc023_01
def test_api_projection_and_immutable_surfaces(monkeypatch):
    state = fake(monkeypatch, body=json.dumps({"version": "2025.1.0", "latitude": 45,
                 "config_dir": "private-filesystem-marker", "location_name": "private-house"}
                ).encode())

    async def exercise():
        api = runtime()
        assert api.__all__ == ["HARestClient", "HARuntimeInfo", "HARestError"]
        client = api.HARestClient(config())
        assert not state.clients and repr(client) == str(client) == "HARestClient(<redacted>)"
        for name in ("request", "post", "get", "send", "write", "to_dict", "__dict__"):
            assert not hasattr(client, name)
        async with client:
            assert not state.clients
            result = await client.runtime_info(correlation_id="call-1")
            assert result.version == "2025.1.0" and result.to_dict() == {"version": "2025.1.0"}
            assert repr(result) == str(result) == "HARuntimeInfo(<redacted>)"
            exported = result.to_dict()
            exported["version"] = "mutated"
            assert result.version == "2025.1.0"
            with pytest.raises(AttributeError):
                result.version = "mutated"
        with pytest.raises(api.HARestError) as caught:
            await client.runtime_info(correlation_id="after-close")
        assert_error(caught.value, "client_closed", "after-close")
        request = state.requests[0]
        assert request.method == "GET" and str(request.url) == URL + "/api/config"
        assert request.headers["Authorization"] == "Bearer " + TOKEN
        assert request.headers["Accept"] == "application/json"
        assert request.headers["Accept-Encoding"] == "identity"
        assert "cookie" not in request.headers
        assert all(s.closed == 1 for s in state.streams)
        assert all(c.closed == 1 for c in state.clients)
        for export in (pickle.dumps, copy.copy, copy.deepcopy, lambda c: c.__getstate__(),
                       lambda c: c.__reduce__(), lambda c: c.__reduce_ex__(4)):
            with pytest.raises(TypeError, match="raw_rest_client_serialization_forbidden"):
                export(client)
        with pytest.raises(TypeError, match="invalid_configuration"):
            api.HARestClient({"private": TOKEN})
        with pytest.raises(RuntimeError, match="client_closed"):
            async with client:
                pass
    run(exercise())


@pytest.mark.tc023_02
@pytest.mark.parametrize("version", ["2025.1.0", "2024.11.0.dev20241014", "2023.9.0b0",
                                      "x", "v" * 128, "printable!~"])
def test_version_positives(monkeypatch, version):
    fake(monkeypatch, body=json.dumps({"version": version}).encode())
    operation = runtime().HARestClient(config()).runtime_info(correlation_id="call-1")
    assert run(operation).version == version


@pytest.mark.tc023_02
@pytest.mark.parametrize("version", [None, 1, True, [], {}, "", "x" * 129, " 2025.1.0",
                                      "2025.1.0 ", "internal space", "tab\t", "\x00",
                                      "\x1f", "\x7f", "版本", TOKEN, URL])
def test_version_negatives(monkeypatch, version):
    fake(monkeypatch, body=json.dumps({"version": version}).encode())
    with pytest.raises(runtime().HARestError) as caught:
        run(runtime().HARestClient(config()).runtime_info(correlation_id="call-1"))
    assert_error(caught.value, "invalid_response")


@pytest.mark.tc023_02
@pytest.mark.parametrize("body", [b'[]', b'null', b'{}', b'{', b'\xff', b'"v"',
    b'{"version":"2025.1.0","version":"2025.1.0"}',
    b'{"version":"2025.1.0","ignored":{"key":1,"key":2}}',
    b'{"version":"2025.1.0","ignored":NaN}',
    b'{"version":"2025.1.0","ignored":Infinity}',
    b'{"version":"2025.1.0","ignored":-Infinity}',
    b'[' * 2000 + b']' * 2000])
def test_json_negatives(monkeypatch, body):
    fake(monkeypatch, body=body)
    with pytest.raises(runtime().HARestError) as caught:
        run(runtime().HARestClient(config()).runtime_info(correlation_id="call-1"))
    assert_error(caught.value, "invalid_response")


@pytest.mark.tc023_02
@pytest.mark.parametrize("headers,valid", [
    ({"Content-Type": "application/json"}, True),
    ({"Content-Type": 'Application/JSON; Charset="UTF-8"'}, True),
    ({"Content-Type": "application/json", "Content-Encoding": "IDENTITY"}, True),
    ({"Content-Type": "text/json"}, False),
    ({"Content-Type": "application/json; charset=latin-1"}, False),
    ({"Content-Type": "application/json; charset=utf-8; charset=utf-8"}, False),
    ({"Content-Type": "application/json, application/json"}, False),
    ({"Content-Type": "application/json", "Content-Encoding": "gzip"}, False),
    ({"Content-Type": "application/json", "Content-Encoding": "deflate"}, False),
    ({"Content-Type": "application/json", "Content-Encoding": "identity, identity"}, False),
    ({"Content-Encoding": "identity"}, False),
])
def test_media_and_encoding(monkeypatch, headers, valid):
    fake(monkeypatch, headers=headers)
    operation = runtime().HARestClient(config()).runtime_info(correlation_id="call-1")
    if valid:
        assert run(operation).version == "2025.1.0"
    else:
        with pytest.raises(runtime().HARestError) as caught:
            run(operation)
        assert_error(caught.value, "invalid_response")


@pytest.mark.tc023_02
@pytest.mark.parametrize("size,valid", [(262143, True), (262144, True), (262145, False)])
@pytest.mark.parametrize("length", [None, "1", "999999"])
def test_stream_cap_independent_of_declared_length(monkeypatch, size, valid, length):
    body = b'{"version":"2025.1.0"}'
    body += b' ' * (size - len(body))
    headers = {"Content-Type": "application/json"}
    if length:
        headers["Content-Length"] = length
    state = fake(monkeypatch, chunks=[body[:100], body[100:]], headers=headers)
    operation = runtime().HARestClient(config()).runtime_info(correlation_id="call-1")
    if valid:
        assert run(operation).version == "2025.1.0"
    else:
        with pytest.raises(runtime().HARestError) as caught:
            run(operation)
        assert_error(caught.value, "invalid_response")
    assert state.streams[0].closed == state.clients[0].closed == 1


@pytest.mark.tc023_03
@pytest.mark.parametrize("status",
                         [201, 204, 301, 302, 303, 307, 308, 400, 401, 403, 404, 429, 500])
def test_status_precedes_body_no_retry(monkeypatch, status):
    state = fake(monkeypatch, status=status, body=TOKEN.encode() * 50000)
    with pytest.raises(runtime().HARestError) as caught:
        run(runtime().HARestClient(config()).runtime_info(correlation_id="call-1"))
    assert_error(caught.value, "auth_failed" if status == 401 else "http_error", status=status)
    assert len(state.requests) == 1 and state.body_reads == 0
    assert state.streams[0].closed == state.clients[0].closed == 1


@pytest.mark.tc023_03
@pytest.mark.parametrize("kind", ["connect", "read", "timeout", "dns", "tls"])
def test_dependency_errors_have_no_raw_chain_and_explicit_recovery(monkeypatch, kind):
    import httpx

    def error(request):
        return (httpx.ReadTimeout if kind == "timeout" else httpx.ConnectError)(
            TOKEN + URL, request=request)
    state = fake(monkeypatch, send_error=error)

    async def exercise():
        client = runtime().HARestClient(config())
        with pytest.raises(runtime().HARestError) as caught:
            await client.runtime_info(correlation_id="call-1")
        assert_error(caught.value, "timeout" if kind == "timeout" else "transport_failed")
        assert len(state.requests) == 1 and state.clients[0].closed == 1
        repaired = fake(monkeypatch)
        assert (await client.runtime_info(correlation_id="second-call")).version == "2025.1.0"
        assert len(repaired.requests) == 1
        await client.aclose()
    run(exercise())


@pytest.mark.tc023_03
@pytest.mark.parametrize("identity", [None, 1, True, [], "", "x" * 65, " has-space", "a/b",
                                       "newline\n", "非ASCII", TOKEN, URL])
def test_invalid_ids_before_closed_busy_and_transport(monkeypatch, identity):
    state = fake(monkeypatch)

    async def exercise():
        client = runtime().HARestClient(config())
        await client.aclose()
        with pytest.raises(runtime().HARestError) as caught:
            await client.runtime_info(correlation_id=identity)
        assert_error(caught.value, "invalid_correlation_id", None)
        assert not state.clients
        with pytest.raises(TypeError):
            await client.runtime_info()
    run(exercise())


@pytest.mark.tc023_03
@pytest.mark.parametrize("identity", ["a", "Z" * 64, "task_01.trace-2"])
def test_valid_id_preserved_exactly(monkeypatch, identity):
    fake(monkeypatch, status=401)
    with pytest.raises(runtime().HARestError) as caught:
        run(runtime().HARestClient(config()).runtime_info(correlation_id=identity))
    assert_error(caught.value, "auth_failed", identity, 401)
    with pytest.raises(AttributeError):
        caught.value.code = "mutated"


@pytest.mark.tc023_04
@pytest.mark.parametrize("budget", [1, 10])
def test_observed_deadline_wins_even_when_body_arrives(monkeypatch, budget):
    async def exercise():
        base = asyncio.get_running_loop().time()
        clock = [base]
        monkeypatch.setattr(runtime(), "_clock", lambda: clock[0])
        async def expire():
            clock[0] = base + budget / 1000
        state = fake(monkeypatch, before=expire)
        with pytest.raises(runtime().HARestError) as caught:
            client = runtime().HARestClient(config(timeout=budget))
            await client.runtime_info(correlation_id="call-1")
        assert_error(caught.value, "timeout")
        assert state.clients[0].closed == state.streams[0].closed == 1
    run(exercise())


@pytest.mark.tc023_04
@pytest.mark.parametrize("cancel_close", [False, True])
def test_single_operation_draining_close_and_waiter_cancellation(monkeypatch, cancel_close):
    async def exercise():
        entered, release = asyncio.Event(), asyncio.Event()
        async def wait():
            entered.set()
            await release.wait()
        state = fake(monkeypatch, before=wait)
        client = runtime().HARestClient(config())
        async def caller():
            result = await client.runtime_info(correlation_id="first")
            # close must wait for operation completion, not this caller's task.
            await asyncio.sleep(0.1)
            return result
        first = asyncio.create_task(caller())
        await entered.wait()
        with pytest.raises(runtime().HARestError) as caught:
            await client.runtime_info(correlation_id="overlap")
        assert_error(caught.value, "client_busy", "overlap")
        closing = asyncio.create_task(client.aclose())
        await asyncio.sleep(0)
        assert not closing.done()
        if cancel_close:
            closing.cancel()
            with pytest.raises(asyncio.CancelledError):
                await closing
            closing = asyncio.create_task(client.aclose())
        with pytest.raises(runtime().HARestError) as caught:
            await client.runtime_info(correlation_id="closing")
        assert_error(caught.value, "client_closed", "closing")
        release.set()
        await asyncio.wait_for(closing, 0.05)
        assert not first.done()
        assert (await first).version == "2025.1.0"
        assert len(state.requests) == 1
        assert state.clients[0].closed == state.streams[0].closed == 1
        assert await client.aclose() is None
    run(exercise())


@pytest.mark.tc023_04
def test_external_cancellation_repeated_during_cleanup(monkeypatch):
    async def exercise():
        entered, cleaning, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
        async def wait():
            entered.set()
            await asyncio.Event().wait()
        async def close():
            cleaning.set()
            await release.wait()
        # Cancel while body reading, so a stream has been assigned.
        state = fake(monkeypatch, close=close)
        original = state
        import httpx
        class Stream(httpx.AsyncByteStream):
            closed = 0
            async def __aiter__(self):
                await wait()
                yield b"unreachable"
            async def aclose(self):
                await close()
                self.closed += 1
        class Client:
            closed = 0
            async def send(self, request):
                original.requests.append(request)
                stream = Stream()
                original.streams.append(stream)
                return httpx.Response(200, headers={"Content-Type": "application/json"},
                                      stream=stream, request=request)
            async def aclose(self):
                self.closed += 1
        def factory():
            client = Client()
            original.clients.append(client)
            return client
        monkeypatch.setattr(runtime(), "_make_client", factory)
        client = runtime().HARestClient(config())
        operation = asyncio.create_task(client.runtime_info(correlation_id="call-1"))
        await entered.wait()
        operation.cancel()
        await cleaning.wait()
        operation.cancel()
        await asyncio.sleep(0)
        assert not operation.done()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await operation
        assert original.clients[0].closed == original.streams[0].closed == 1
        repaired = fake(monkeypatch)
        assert (await client.runtime_info(correlation_id="recovery")).version == "2025.1.0"
        assert len(repaired.requests) == 1
        await client.aclose()
    run(exercise())


@pytest.mark.tc023_04
def test_cleanup_guard_cannot_extend_success(monkeypatch):
    async def blocked_close():
        await asyncio.sleep(10)
    state = fake(monkeypatch, close=blocked_close)
    monkeypatch.setattr(runtime(), "_CLEANUP_SECONDS", 0.02)
    started = time.monotonic()
    with pytest.raises(runtime().HARestError) as caught:
        run(runtime().HARestClient(config()).runtime_info(correlation_id="call-1"))
    assert_error(caught.value, "timeout")
    assert time.monotonic() - started < 0.5
    assert state.streams[0].closed == state.clients[0].closed == 1


@pytest.mark.tc023_05
def test_real_loopback_headers_no_cookie_reuse_and_info_logs(caplog, monkeypatch):
    caplog.set_level(logging.INFO)
    monkeypatch.setenv("HTTP_PROXY", "http://must-not-be-used.invalid:1")
    monkeypatch.setenv("HTTPS_PROXY", "http://must-not-be-used.invalid:1")
    monkeypatch.setenv("SSL_CERT_FILE", "/nonexistent/private-cert-path")
    with server(headers={"Set-Cookie": "private-cookie=never-repeat"}) as (url, requests):
        async def exercise():
            async with runtime().HARestClient(config(url)) as client:
                for number in range(2):
                    info = await client.runtime_info(correlation_id=f"call-{number}")
                    assert info.version == "2025.1.0"
        run(exercise())
        assert len(requests) == 2
        for method, path, headers in requests:
            assert method == "GET" and path == "/api/config"
            assert headers["Authorization"] == "Bearer " + TOKEN
            assert headers["Accept"] == "application/json"
            assert headers["Accept-Encoding"] == "identity"
            assert "Cookie" not in headers
        assert TOKEN not in caplog.text and url not in caplog.text


@pytest.mark.tc023_05
def test_redirect_second_destination_has_zero_requests():
    with server() as (destination, second):
        with server(status=302, headers={"Location": destination + "/api/config"}) as (url, first):
            with pytest.raises(runtime().HARestError) as caught:
                run(runtime().HARestClient(config(url)).runtime_info(correlation_id="call-1"))
            assert_error(caught.value, "http_error", status=302)
            assert len(first) == 1 and second == []


@pytest.mark.tc023_05
def test_real_connection_refusal_and_dns_failure(monkeypatch):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        # Bound but not listening, so no port-reuse race with another process.
        with pytest.raises(runtime().HARestError) as caught:
            run(runtime().HARestClient(config(f"http://127.0.0.1:{port}"))
                .runtime_info(correlation_id="call-1"))
    assert_error(caught.value, "transport_failed")
    def denied_dns(*args, **kwargs):
        raise socket.gaierror(TOKEN + URL)
    monkeypatch.setattr(socket, "getaddrinfo", denied_dns)
    with pytest.raises(runtime().HARestError) as caught:
        run(runtime().HARestClient(config("http://dns-failure.invalid"))
            .runtime_info(correlation_id="dns-call"))
    assert_error(caught.value, "transport_failed", "dns-call")


@pytest.mark.tc023_05
def test_real_tls_certificate_verification(tmp_path):
    # Fictional key generated in tmp; never tracked or printed. Explicit TLS
    # fixture subprocess boundary, independent of runtime secret loading.
    key, cert = tmp_path / "key.pem", tmp_path / "cert.pem"
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                    "-keyout", str(key), "-out", str(cert), "-days", "1",
                    "-subj", "/CN=localhost"], check=True, capture_output=True, timeout=20)
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(cert, key)
    with server(tls=tls) as (url, requests):
        with pytest.raises(runtime().HARestError) as caught:
            run(runtime().HARestClient(config(url)).runtime_info(correlation_id="tls-call"))
        assert_error(caught.value, "transport_failed", "tls-call")
        assert requests == []


@pytest.mark.tc023_04
@pytest.mark.parametrize("trickle", [False, True])
def test_real_overall_deadline_headers_and_trickle(trickle):
    with server(delay=0 if trickle else 0.2, trickle=trickle) as (url, requests):
        started = time.monotonic()
        with pytest.raises(runtime().HARestError) as caught:
            client = runtime().HARestClient(config(url, timeout=80))
            run(client.runtime_info(correlation_id="call-1"))
        assert_error(caught.value, "timeout")
        assert time.monotonic() - started < 0.8  # Explicit scheduler tolerance.
        assert len(requests) == 1
