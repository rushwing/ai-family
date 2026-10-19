"""REQ-031 proposed adversarial discovery verification; fictional HA only."""

import asyncio
import builtins
import copy
import importlib
import json
import pickle
import traceback
from dataclasses import FrozenInstanceError

import pytest
from ha_discovery_artifact_smoke import COMMANDS, COMPONENTS, TOKEN, check, fixture
from test_ha_websocket import Socket, configuration

pytestmark = pytest.mark.ha_websocket_async
AUTH = ['{"type":"auth_required"}', '{"type":"auth_ok"}']


def runtime():
    return importlib.import_module("home_device_fabric.ha_discovery")


def frames(data=None):
    records = fixture() if data is None else data
    return [
        json.dumps({"id": i, "type": "result", "success": True, "result": records[label]})
        for i, label in enumerate(COMPONENTS, 1)
    ]


def fake(monkeypatch, sockets):
    attempts = []

    async def connect(config, limit):
        attempts.append((config, limit))
        socket = sockets.pop(0)
        if isinstance(socket, BaseException):
            raise socket
        return socket

    monkeypatch.setattr(runtime(), "_open", connect)
    return attempts


async def rejected(client, code, stage, completed=()):
    with pytest.raises(runtime().HADiscoveryError) as caught:
        await client.discover()
    error = caught.value
    assert error.to_dict() == {"code": code, "stage": stage, "completed": list(completed)}
    assert error.__context__ is None and error.__cause__ is None
    assert TOKEN not in str(error) + repr(error) + repr(error.to_dict())
    assert TOKEN not in "".join(traceback.format_exception(error))
    return error


@pytest.mark.tc031_01
@pytest.mark.ha_websocket_pure
@pytest.mark.parametrize(
    "field,bad,error",
    [
        ("configuration", None, TypeError),
        ("configuration", {}, TypeError),
        ("configuration", True, TypeError),
        *[
            ("max_response_bytes", x, ValueError)
            for x in (True, 4095, 4194305, 4096.0, "4096", None)
        ],
        *[("max_records", x, ValueError) for x in (True, 0, 10001, 1.0, "1", None)],
    ],
)
def test_strict_constructor(field, bad, error):
    args = {"configuration": configuration(), field: bad}
    with pytest.raises(error):
        runtime().HARegistryDiscoveryClient(**args)


@pytest.mark.tc031_01
@pytest.mark.tc031_04
@pytest.mark.ha_websocket_pure
def test_construction_no_file_io_reinit_and_serialization(monkeypatch, offline):
    mod = runtime()
    config = configuration()

    def denied(*args, **kwargs):
        pytest.fail("construction file I/O")

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", denied)
        client = mod.HARegistryDiscoveryClient(config)
    assert repr(client) == "HARegistryDiscoveryClient(<redacted>)" and offline == []
    with pytest.raises(RuntimeError, match="^client_initialized$"):
        client.__init__(config)
    for clone in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(TypeError, match="serialization_forbidden"):
            clone(client)


@pytest.mark.tc031_01
@pytest.mark.parametrize("empty", [False, True])
def test_complete_bundle_command_order_and_repeat_calls(monkeypatch, empty):
    async def scenario():
        data = dict(zip(COMPONENTS, ([], [], [], []))) if empty else fixture()
        sockets = [Socket(AUTH + frames(data)), Socket(AUTH + frames(data))]
        first, second = sockets
        attempts = fake(monkeypatch, sockets)
        client = runtime().HARegistryDiscoveryClient(configuration())
        initial = await client.discover()
        assert initial.for_mapping() == data
        assert initial.to_redacted_dict() == {
            "complete": True,
            "counts": dict.fromkeys(COMPONENTS, int(not empty)),
        }
        assert first.sent == [
            {"type": "auth", "access_token": configuration().access_token_for_transport()},
            *[{"id": i, "type": name} for i, name in enumerate(COMMANDS, 1)],
        ]
        assert first.closed == 1 and first.aborted == 0
        assert (await client.discover()).for_mapping() == data
        assert len(attempts) == 2 and second.closed == 1
        detached = initial.for_mapping()
        detached["devices"].append({"id": "new"})
        assert initial.for_mapping() == data
        projection = initial.to_redacted_dict()
        projection["counts"].clear()
        assert initial.to_redacted_dict()["counts"] == dict.fromkeys(COMPONENTS, int(not empty))
        with pytest.raises(FrozenInstanceError):
            initial._counts = ()
        for clone in (copy.copy, copy.deepcopy, pickle.dumps):
            with pytest.raises(TypeError, match="serialization_forbidden"):
                clone(initial)
        assert repr(initial) == "HADiscoverySnapshot(<redacted>)"
        assert TOKEN not in repr(initial) + repr(initial.to_redacted_dict())
        await client.aclose()

    asyncio.run(scenario())


@pytest.mark.tc031_01
def test_raw_optional_fields_and_mismatched_sets_are_preserved(monkeypatch):
    async def scenario():
        data = fixture()
        data["entities"].append(
            {
                "entity_id": "sensor.unassigned",
                "device_id": None,
                "area_id": "removed-area",
                "disabled_by": "user",
            }
        )
        data["states"].append(
            {
                "entity_id": "sensor.unregistered",
                "state": "unknown",
                "attributes": {"zero": 0, "false": False, "none": None},
            }
        )
        data["devices"][0]["future_field"] = [1, {"private": TOKEN}]
        fake(monkeypatch, [Socket(AUTH + frames(data))])
        async with runtime().HARegistryDiscoveryClient(configuration()) as client:
            assert (await client.discover()).for_mapping() == data

    asyncio.run(scenario())


@pytest.mark.tc031_02
@pytest.mark.parametrize("component", range(4))
@pytest.mark.parametrize(
    "failure,code",
    [
        ("unauthorized", "permission_denied"),
        ("not_allowed", "permission_denied"),
        ("unknown_command", "unsupported_command"),
        ("peer_private_error", "command_failed"),
    ],
)
def test_partial_command_failure_is_explicit_and_stops(monkeypatch, component, failure, code):
    async def scenario():
        messages = frames()
        messages[component] = json.dumps(
            {
                "id": component + 1,
                "type": "result",
                "success": False,
                "error": {"code": failure, "message": TOKEN},
            }
        )
        socket = Socket(AUTH + messages)
        attempts = fake(monkeypatch, [socket])
        client = runtime().HARegistryDiscoveryClient(configuration())
        error = await rejected(client, code, COMPONENTS[component], COMPONENTS[:component])
        assert len(socket.sent) == component + 2 and len(attempts) == 1 and socket.closed == 1
        projection = error.to_dict()
        projection["completed"].clear()
        assert error.completed == COMPONENTS[:component]
        with pytest.raises(AttributeError):
            error.code = "timeout"
        await client.aclose()

    asyncio.run(scenario())


@pytest.mark.tc031_02
@pytest.mark.parametrize(
    "bad,code",
    [
        (b"{}", "invalid_response"),
        ("[]", "invalid_response"),
        ("null", "invalid_response"),
        ('{"id":1,"id":1}', "invalid_response"),
        ('{"id":1,"private":NaN}', "invalid_response"),
        ('{"id":1,"private":1e999}', "invalid_response"),
        ('{"id":1,"private":Infinity}', "invalid_response"),
        ("{", "invalid_response"),
        ("\ud800", "invalid_response"),
        (
            json.dumps({"id": True, "type": "result", "success": True, "result": []}),
            "invalid_response",
        ),
        (
            json.dumps({"id": 2, "type": "result", "success": True, "result": []}),
            "invalid_response",
        ),
        (
            json.dumps({"id": 1.0, "type": "result", "success": True, "result": []}),
            "invalid_response",
        ),
        (json.dumps({"id": 1, "type": "event", "success": True, "result": []}), "invalid_response"),
        (json.dumps({"id": 1, "type": "result", "success": 1, "result": []}), "invalid_response"),
        (json.dumps({"id": 1, "type": "result", "success": True}), "invalid_response"),
        (
            json.dumps({"id": 1, "type": "result", "success": False, "error": TOKEN}),
            "invalid_response",
        ),
        (
            json.dumps({"id": 1, "type": "result", "success": False, "error": {"code": True}}),
            "invalid_response",
        ),
        ('{"private":"' + "x" * 4096 + '"}', "response_limit"),
        ('{"private":' + "[" * 34 + "0" + "]" * 34 + "}", "response_limit"),
    ],
)
def test_strict_wire_validation(monkeypatch, bad, code):
    async def scenario():
        socket = Socket(AUTH + [bad])
        fake(monkeypatch, [socket])
        client = runtime().HARegistryDiscoveryClient(
            configuration(timeout=100), max_response_bytes=4096
        )
        await rejected(client, code, "devices")
        assert socket.closed == 1 and len(socket.sent) == 2
        await client.aclose()

    asyncio.run(scenario())


@pytest.mark.tc031_02
@pytest.mark.parametrize(
    "component,raw",
    [
        ("devices", '{"id":2,"id":1,"type":"result","success":true,"result":[]}'),
        ("devices", '{"id":1,"type":"result","success":false,"success":true,"result":[]}'),
        (
            "devices",
            '{"id":1,"type":"result","success":true,"result":[{"id":"'
            + TOKEN
            + '","id":"device"}]}',
        ),
        (
            "states",
            '{"id":4,"type":"result","success":true,"result":[{"entity_id":"sensor.x",'
            '"state":"on","attributes":{"k":"' + TOKEN + '","k":2}}]}',
        ),
    ],
    ids=["envelope-id", "envelope-success", "record-id", "nested-attributes"],
)
def test_duplicate_json_keys_reject_otherwise_valid_last_wins(monkeypatch, component, raw):
    # A permissive decoder would accept every frame, so no other validation can
    # accidentally satisfy the rejection assertion when unique-key checks regress.
    index = COMPONENTS.index(component)
    assert json.loads(raw)["success"] is True

    async def scenario():
        messages = frames()
        messages[index] = raw
        socket = Socket(AUTH + messages)
        attempts = fake(monkeypatch, [socket])
        client = runtime().HARegistryDiscoveryClient(configuration())
        await rejected(client, "invalid_response", component, COMPONENTS[:index])
        assert len(socket.sent) == index + 2 and len(attempts) == 1
        assert socket.closed == 1 and socket.aborted == 0 and client._worker is None
        await client.aclose()

    asyncio.run(scenario())


@pytest.mark.tc031_02
@pytest.mark.parametrize(
    "component,rows,code",
    [
        ("devices", None, "invalid_response"),
        ("devices", [{}], "invalid_response"),
        ("devices", [False], "invalid_response"),
        ("devices", [{"id": True}], "invalid_response"),
        ("devices", [{"id": ""}], "invalid_response"),
        ("devices", [{"id": "x" * 513}], "invalid_response"),
        ("devices", [{"id": "same"}, {"id": "same"}], "invalid_response"),
        ("devices", [{"id": "one"}, {"id": "two"}], "response_limit"),
        ("devices", [{"id": "one", "area_id": False}], "invalid_response"),
        ("entities", [{"entity_id": "x", "device_id": []}], "invalid_response"),
        ("entities", [{"entity_id": "x", "area_id": ""}], "invalid_response"),
        ("entities", [{"entity_id": "same"}, {"entity_id": "same"}], "invalid_response"),
        ("areas", [{"area_id": "a"}], "invalid_response"),
        ("areas", [{"area_id": "a", "name": ""}], "invalid_response"),
        ("states", [{"entity_id": "s", "state": True, "attributes": {}}], "invalid_response"),
        ("states", [{"entity_id": "s", "state": "on", "attributes": []}], "invalid_response"),
        ("states", [{"entity_id": "s", "state": "x" * 4097, "attributes": {}}], "invalid_response"),
    ],
)
def test_records_are_validated_before_publication(monkeypatch, component, rows, code):
    async def scenario():
        data = fixture()
        data[component] = rows
        socket = Socket(AUTH + frames(data))
        fake(monkeypatch, [socket])
        client = runtime().HARegistryDiscoveryClient(
            configuration(), max_records=1 if code == "response_limit" else 2
        )
        index = COMPONENTS.index(component)
        await rejected(client, code, component, COMPONENTS[:index])
        assert socket.closed == 1 and len(socket.sent) == index + 2
        await client.aclose()

    asyncio.run(scenario())


@pytest.mark.tc031_02
@pytest.mark.tc031_03
@pytest.mark.parametrize(
    "messages,code",
    [
        (['{"type":"auth_invalid","message":"' + TOKEN + '"}'], "auth_failed"),
        ([AUTH[0], '{"type":"auth_invalid","message":"' + TOKEN + '"}'], "auth_failed"),
        (['{"type":"auth_ok"}'], "invalid_response"),
        ([AUTH[0], "{}"], "invalid_response"),
        ([OSError(TOKEN)], "transport_failed"),
        ([RuntimeError(TOKEN)], "internal_error"),
    ],
)
def test_authentication_and_transport_failures_never_send_commands(monkeypatch, messages, code):
    async def scenario():
        socket = Socket(messages)
        attempts = fake(monkeypatch, [socket])
        client = runtime().HARegistryDiscoveryClient(configuration())
        await rejected(client, code, "auth")
        assert all(item["type"] == "auth" for item in socket.sent)
        assert socket.closed == 1 and len(attempts) == 1
        await client.aclose()

    asyncio.run(scenario())


@pytest.mark.tc031_03
def test_failed_call_does_not_cache_partial_data_and_can_retry_explicitly(monkeypatch):
    async def scenario():
        partial = Socket(AUTH + frames()[:2] + [OSError(TOKEN)])
        recovery = Socket(AUTH + frames())
        attempts = fake(monkeypatch, [partial, recovery])
        client = runtime().HARegistryDiscoveryClient(configuration())
        await rejected(client, "transport_failed", "areas", COMPONENTS[:2])
        assert len(attempts) == 1
        assert (await client.discover()).for_mapping() == fixture()
        assert len(attempts) == 2 and partial.closed == recovery.closed == 1
        assert client._worker is None
        await client.aclose()

    asyncio.run(scenario())


@pytest.mark.tc031_03
@pytest.mark.parametrize("stage", ["connect", "auth", "devices", "entities", "areas", "states"])
def test_timeout_stops_each_stage_and_no_retry(monkeypatch, stage):
    async def scenario():
        socket = None
        if stage == "connect":

            async def connect(*args):
                await asyncio.Future()

            monkeypatch.setattr(runtime(), "_open", connect)
        else:
            count = COMPONENTS.index(stage) if stage != "auth" else -1
            socket = Socket([] if stage == "auth" else AUTH + frames()[:count])
            fake(monkeypatch, [socket])
        client = runtime().HARegistryDiscoveryClient(configuration(timeout=15))
        completed = () if stage in ("auth", "connect") else COMPONENTS[: COMPONENTS.index(stage)]
        await rejected(client, "timeout", "auth" if stage == "connect" else stage, completed)
        if socket is not None:
            assert socket.closed == 1
        assert client._worker is None
        await client.aclose()

    asyncio.run(scenario())


@pytest.mark.tc031_03
def test_deadline_is_shared_across_commands(monkeypatch):
    async def scenario():
        loop = asyncio.get_running_loop()
        base = loop.time()
        elapsed = [0.0]

        class SlowSocket(Socket):
            async def recv(self):
                if len(self.sent) > 1:
                    elapsed[0] += 0.025
                return await super().recv()

        socket = SlowSocket(AUTH + frames())
        fake(monkeypatch, [socket])
        client = runtime().HARegistryDiscoveryClient(configuration(timeout=40))
        with monkeypatch.context() as patch:
            patch.setattr(loop, "time", lambda: base + elapsed[0])
            await rejected(client, "timeout", "entities", ("devices", "entities"))
        assert len(socket.sent) == 3 and socket.closed == 1
        await client.aclose()

    asyncio.run(scenario())


@pytest.mark.tc031_03
def test_busy_close_and_discover_after_close(monkeypatch):
    async def scenario():
        socket = Socket(AUTH)
        attempts = fake(monkeypatch, [socket])
        client = runtime().HARegistryDiscoveryClient(configuration())
        running = asyncio.create_task(client.discover())
        await socket.waiting.wait()
        await rejected(client, "client_busy", "operation")
        await asyncio.gather(client.aclose(), client.aclose())
        with pytest.raises(asyncio.CancelledError):
            await running
        assert socket.closed == 1 and len(attempts) == 1 and client._worker is None
        await rejected(client, "client_closed", "operation")
        with pytest.raises(runtime().HADiscoveryError, match="client_closed"):
            async with client:
                pytest.fail("closed context entered")

    asyncio.run(scenario())


@pytest.mark.tc031_03
@pytest.mark.parametrize("close_waiter", [False, True])
def test_repeated_cancellation_drains_owned_cleanup(monkeypatch, close_waiter):
    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()

        async def close():
            entered.set()
            await release.wait()

        socket = Socket(AUTH, close=close)
        fake(monkeypatch, [socket])
        client = runtime().HARegistryDiscoveryClient(configuration())
        running = asyncio.create_task(client.discover())
        await socket.waiting.wait()
        waiter = asyncio.create_task(client.aclose()) if close_waiter else running
        if not close_waiter:
            running.cancel()
        await entered.wait()
        waiter.cancel()
        await asyncio.sleep(0)
        waiter.cancel()
        await asyncio.sleep(0)
        assert not running.done()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await running
        if close_waiter:
            with pytest.raises(asyncio.CancelledError):
                await waiter
        await client.aclose()
        assert socket.closed == 1 and socket.aborted == 0 and client._worker is None
        owned = [
            t
            for t in asyncio.all_tasks()
            if t is not asyncio.current_task() and t.get_name().startswith("ha-discovery")
        ]
        assert owned == []

    asyncio.run(scenario())


@pytest.mark.tc031_03
def test_close_during_successful_acquisition_cleanup_never_publishes(monkeypatch):
    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()

        async def close():
            entered.set()
            await release.wait()

        socket = Socket(AUTH + frames(), close=close)
        fake(monkeypatch, [socket])
        client = runtime().HARegistryDiscoveryClient(configuration())
        async with asyncio.timeout(2):
            running = asyncio.create_task(client.discover())
            await entered.wait()  # All four reads succeeded; only cleanup remains.
            assert len(socket.sent) == 5
            closing = asyncio.create_task(client.aclose())
            await asyncio.sleep(0)
            assert client._closed and not running.done() and not closing.done()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await running
            await closing
        await client.aclose()
        assert socket.closed == 1 and socket.aborted == 0 and client._worker is None
        assert not any(
            task.get_name().startswith("ha-discovery")
            for task in asyncio.all_tasks()
            if task is not asyncio.current_task()
        )

    asyncio.run(scenario())


@pytest.mark.tc031_03
@pytest.mark.parametrize("primary", [False, True])
def test_cleanup_failure_rejects_success_without_masking_primary(monkeypatch, primary):
    async def scenario():
        async def bad_close():
            raise OSError(TOKEN)

        socket = Socket(AUTH + ([OSError(TOKEN)] if primary else frames()), close=bad_close)
        fake(monkeypatch, [socket])
        client = runtime().HARegistryDiscoveryClient(configuration())
        await rejected(
            client,
            "transport_failed" if primary else "cleanup_failed",
            "devices" if primary else "cleanup",
            () if primary else COMPONENTS,
        )
        assert socket.closed == 1 and socket.aborted == 1
        await client.aclose()

    asyncio.run(scenario())


@pytest.mark.tc031_03
def test_hung_close_aborts_within_bound(monkeypatch):
    async def scenario():
        async def hung():
            await asyncio.Future()

        socket = Socket(AUTH + frames(), close=hung)
        fake(monkeypatch, [socket])
        client = runtime().HARegistryDiscoveryClient(configuration())
        async with asyncio.timeout(2):
            await rejected(client, "cleanup_failed", "cleanup", COMPONENTS)
        assert socket.aborted == 1
        await client.aclose()

    asyncio.run(scenario())


@pytest.mark.tc031_03
def test_close_before_first_call_and_loop_ownership(monkeypatch):
    client = runtime().HARegistryDiscoveryClient(configuration())

    async def first():
        await client.aclose()
        await client.aclose()
        await rejected(client, "client_closed", "operation")

    asyncio.run(first())
    with pytest.raises(RuntimeError, match="^wrong_event_loop$"):
        asyncio.run(client.discover())


@pytest.mark.tc031_02
@pytest.mark.parametrize(
    "raw",
    [
        '{"id":1,"type":"result","success":true,"result":[{"id":"\\ud800"}]}',
        '{"id":1,"type":"result","success":true,"result":[{"id":"x","\\ud800":1}]}',
        '{"id":1,"type":"result","success":true,"result":[{"id":"x","extra":"\\udfff"}]}',
    ],
)
def test_json_escaped_surrogates_are_not_retained(monkeypatch, raw):
    async def scenario():
        socket = Socket(AUTH + [raw])
        fake(monkeypatch, [socket])
        client = runtime().HARegistryDiscoveryClient(configuration(timeout=100))
        await rejected(client, "invalid_response", "devices")
        assert socket.closed == 1
        await client.aclose()

    asyncio.run(scenario())


@pytest.mark.tc031_02
@pytest.mark.tc031_03
@pytest.mark.parametrize(
    "status,code",
    [
        (401, "auth_failed"),
        (403, "auth_failed"),
        (302, "invalid_response"),
        (500, "invalid_response"),
    ],
)
def test_handshake_http_status_is_finite_and_never_retried(monkeypatch, status, code):
    from websockets.datastructures import Headers
    from websockets.exceptions import InvalidStatus
    from websockets.http11 import Response

    async def scenario():
        error = InvalidStatus(Response(status, TOKEN, Headers(), b"private-body"))
        attempts = fake(monkeypatch, [error])
        client = runtime().HARegistryDiscoveryClient(configuration())
        await rejected(client, code, "auth")
        assert len(attempts) == 1
        await client.aclose()

    asyncio.run(scenario())


@pytest.mark.tc031_02
@pytest.mark.parametrize(
    "close_code,expected",
    [(1009, "response_limit"), (1007, "invalid_response"), (1000, "transport_failed")],
)
def test_remote_close_is_finite_and_owned_socket_closes(monkeypatch, close_code, expected):
    from websockets.exceptions import ConnectionClosedError
    from websockets.frames import Close

    async def scenario():
        error = ConnectionClosedError(None, Close(close_code, TOKEN))
        socket = Socket(AUTH + [error])
        fake(monkeypatch, [socket])
        client = runtime().HARegistryDiscoveryClient(configuration())
        await rejected(client, expected, "devices")
        assert socket.closed == 1
        await client.aclose()

    asyncio.run(scenario())


@pytest.mark.tc031_03
def test_close_during_connection_does_not_leave_owned_tasks(monkeypatch):
    async def scenario():
        entered = asyncio.Event()

        async def connect(*args):
            entered.set()
            await asyncio.Future()

        monkeypatch.setattr(runtime(), "_open", connect)
        client = runtime().HARegistryDiscoveryClient(configuration())
        running = asyncio.create_task(client.discover())
        await entered.wait()
        await client.aclose()
        with pytest.raises(asyncio.CancelledError):
            await running
        assert client._worker is None and client._closer.done()
        await rejected(client, "client_closed", "operation")

    asyncio.run(scenario())


@pytest.mark.tc031_03
def test_process_control_exception_propagates_after_cleanup(monkeypatch):
    class ProcessControl(BaseException):
        pass

    async def scenario():
        socket = Socket(AUTH + [ProcessControl()])
        fake(monkeypatch, [socket])
        client = runtime().HARegistryDiscoveryClient(configuration())
        with pytest.raises(ProcessControl):
            await client.discover()
        assert socket.closed == 1 and client._worker is None
        await client.aclose()

    asyncio.run(scenario())


@pytest.mark.tc031_03
@pytest.mark.parametrize("secure", [False, True])
def test_production_connection_uses_accepted_wire_policy(monkeypatch, secure):
    async def scenario():
        captured = []
        sentinel = object()

        async def connect(uri, **kwargs):
            captured.append((uri, kwargs))
            return sentinel

        mod = runtime()
        trust = object()
        monkeypatch.setattr(mod, "_NoRedirectConnect", connect)
        monkeypatch.setattr(mod, "_tls_context", lambda: trust)
        config = configuration(
            url="https://fixture.invalid:8123" if secure else "http://fixture.invalid:8123"
        )
        assert await mod._open(config, 8192) is sentinel
        uri, policy = captured[0]
        assert uri == ("wss" if secure else "ws") + "://fixture.invalid:8123/api/websocket"
        assert policy == {
            "proxy": None,
            "compression": None,
            "additional_headers": None,
            "user_agent_header": None,
            "open_timeout": 10,
            "close_timeout": 1,
            "ping_interval": 20,
            "ping_timeout": 20,
            "max_size": 8192,
            "max_queue": 4,
            "logger": mod._WIRE_LOGGER,
            "ssl": trust if secure else None,
        }
        assert policy["logger"].disabled and not policy["logger"].propagate

    asyncio.run(scenario())


@pytest.mark.tc031_01
@pytest.mark.tc031_02
def test_wire_byte_limit_counts_utf8_and_accepts_exact_boundary(monkeypatch):
    async def scenario():
        records = fixture()
        socket = Socket(AUTH + frames(records))
        fake(monkeypatch, [socket])
        # Pad the first JSON frame to the exact configured byte boundary.
        first = json.loads(socket.messages[2])
        base = json.dumps(first, ensure_ascii=False, separators=(",", ":"))
        first["padding"] = "é" * ((4096 - len(base.encode()) - len(',"padding":""')) // 2)
        raw = json.dumps(first, ensure_ascii=False, separators=(",", ":"))
        raw += " " * (4096 - len(raw.encode()))
        assert len(raw.encode()) == 4096
        socket.messages[2] = raw
        client = runtime().HARegistryDiscoveryClient(configuration(), max_response_bytes=4096)
        assert (await client.discover()).for_mapping() == records
        overflow = Socket(AUTH + [raw + "é"])
        fake(monkeypatch, [overflow])
        await rejected(client, "response_limit", "devices")
        assert overflow.closed == 1
        await client.aclose()

    asyncio.run(scenario())


@pytest.mark.tc031_03
@pytest.mark.tc031_04
@pytest.mark.ha_websocket_wire
def test_real_loopback_installed_checks():
    assert asyncio.run(check()) == {"checks": 15, "loopback": True, "device_writes": 0}
