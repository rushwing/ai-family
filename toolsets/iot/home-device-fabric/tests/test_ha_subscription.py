"""REQ-027 proposed verification with literal protocol fixtures; no private HA."""

import asyncio
import builtins
import copy
import importlib
import io
import json
import logging
import os
import pickle
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from test_ha_websocket import Socket, configuration, fake

pytestmark = pytest.mark.ha_websocket_async
ACK = '{"id":1,"type":"result","success":true,"result":null}'
EVENT = ('{"id":1,"type":"event","event":{"event_type":"state_changed",'
         '"data":{"entity_id":"light.fixture","old_state":null,'
         '"new_state":{"state":"on","attributes":{"brightness":42}}},'
         '"time_fired":"2026-10-17T10:00:00+00:00"}}')
AUTH = ['{"type":"auth_required"}', '{"type":"auth_ok"}']
COMMAND = {"id": 1, "type": "subscribe_events", "event_type": "state_changed"}


def runtime():
    return importlib.import_module("home_device_fabric.ha_subscription")


async def wait_for(predicate):
    async with asyncio.timeout(3):
        while not predicate():
            await asyncio.sleep(0)


async def finish(client):
    async with asyncio.timeout(3):
        await client.run()


async def consume(event):
    pass


@pytest.mark.tc027_01
def test_api_ack_boundary_and_detached_health(monkeypatch):
    async def scenario():
        socket = Socket(AUTH)
        attempts = fake(monkeypatch, [socket])
        mod = runtime()
        client = mod.HAStateSubscriptionClient(configuration(), consume)
        initial = client.subscription_health()
        assert initial.to_dict() == {"state": "idle", "reason": None,
                                     "sequence": 0, "subscribed": False}
        assert attempts.attempts == 0
        with pytest.raises(FrozenInstanceError):
            initial.state = "subscribed"
        view = initial.to_dict()
        view["state"] = "subscribed"
        assert initial.state == "idle"
        running = asyncio.create_task(client.run())
        try:
            await socket.waiting.wait()
            assert client.health().state == "connected"
            assert client.subscription_health().to_dict() == {
                "state": "subscribing", "reason": None, "sequence": 1, "subscribed": False}
            assert socket.sent == [{"type": "auth", "access_token":
                                    "fictional-websocket-credential-7249"}, COMMAND]
            with pytest.raises(RuntimeError, match="^client_started$"):
                await finish(client)
        finally:
            await client.aclose()
            await running
        assert client.subscription_health().state == "closed"
        assert not client.subscription_health().subscribed
        assert initial.sequence == 0
        with pytest.raises(RuntimeError, match="^client_closed$"):
            await finish(client)
    asyncio.run(scenario())


@pytest.mark.parametrize("field,value,error", [
    ("configuration", None, TypeError), ("configuration", {}, TypeError),
    ("callback", None, TypeError), ("callback", 1, TypeError),
    ("delivery_timeout_ms", True, ValueError), ("delivery_timeout_ms", 0, ValueError),
    ("delivery_timeout_ms", 60001, ValueError), ("delivery_timeout_ms", 1.0, ValueError),
    ("delivery_timeout_ms", "1", ValueError),
])
@pytest.mark.tc027_01
@pytest.mark.ha_websocket_pure
def test_constructor_rejects_before_io(field, value, error):
    args = {"configuration": configuration(), "callback": consume}
    args[field] = value
    with pytest.raises(error):
        runtime().HAStateSubscriptionClient(**args)


@pytest.mark.parametrize("values", [
    {"state": "raw-secret"}, {"state": []}, {"reason": "raw-secret"}, {"reason": []},
    {"sequence": True}, {"sequence": -1}, {"sequence": 0.0},
])
@pytest.mark.tc027_01
@pytest.mark.ha_websocket_pure
def test_health_rejects_nonfinite_values(values):
    with pytest.raises(ValueError, match="^invalid_subscription_health$"):
        runtime().HASubscriptionHealth(**values)


@pytest.mark.tc027_01
@pytest.mark.ha_websocket_pure
def test_construction_no_io_and_reinitialization(monkeypatch):
    mod, config = runtime(), configuration()
    attempts = []

    def denied(*args, **kwargs):
        attempts.append(1)
        raise AssertionError("construction attempted I/O")

    class Environment(dict):
        __getitem__ = get = __iter__ = denied

    with monkeypatch.context() as patch:
        for owner, name in ((builtins, "open"), (io, "open"), (os, "open"),
                            (Path, "open"), (asyncio, "new_event_loop")):
            patch.setattr(owner, name, denied)
        patch.setattr(os, "environ", Environment())
        client = mod.HAStateSubscriptionClient(config, consume)
        assert client.subscription_health().state == "idle"
    assert attempts == []
    with pytest.raises(RuntimeError, match="^client_initialized$"):
        client.__init__(configuration(), consume)


@pytest.mark.parametrize("message,reason", [
    ('{"id":1,"type":"result","success":false,"error":{"message":"secret"}}',
     "subscription_rejected"),
    ('{"id":2,"type":"result","success":true,"result":null}', "protocol_error"),
    ('{"id":true,"type":"result","success":true,"result":null}', "protocol_error"),
    ('{"id":1.0,"type":"result","success":true,"result":null}', "protocol_error"),
    ('{"id":1,"type":"result","success":1,"result":null}', "protocol_error"),
    ('{"id":1,"type":"result","success":true}', "protocol_error"),
    ('{"id":1,"type":"result","success":true,"result":{}}', "protocol_error"),
    ('{"id":1,"id":1,"type":"result","success":true,"result":null}', "protocol_error"),
    (EVENT, "protocol_error"), ('[]', "protocol_error"), (b'{}', "protocol_error"),
])
@pytest.mark.tc027_02
def test_ack_rejection_and_invalid_frames(monkeypatch, message, reason):
    async def scenario():
        socket = Socket(AUTH + [message])
        attempts = fake(monkeypatch, [socket])
        delivered = []

        async def callback(event):
            delivered.append(event)

        client = runtime().HAStateSubscriptionClient(configuration(), callback)
        await finish(client)
        health = client.subscription_health()
        assert health.reason == reason and not health.subscribed
        assert health.state == ("rejected" if reason == "subscription_rejected" else "failed")
        assert attempts.attempts == 1 and socket.closed == 1 and delivered == []
        assert socket.sent[1:] == [COMMAND]
        await client.aclose()
    asyncio.run(scenario())


@pytest.mark.parametrize("message", [
    EVENT.replace('"id":1', '"id":2'), EVENT.replace('"id":1', '"id":true'),
    EVENT.replace('"state_changed"', '"other_event"'),
    EVENT.replace('"entity_id":"light.fixture"', '"entity_id":1'),
    EVENT.replace('"entity_id":"light.fixture"', '"entity_id":""'),
    EVENT.replace('"old_state":null,', ''),
    EVENT.replace('"old_state":null', '"old_state":false'),
    EVENT.replace('"brightness":42', '"brightness":NaN'),
    EVENT.replace('"brightness":42', '"brightness":1e999'),
    EVENT.replace('"brightness":42', '"brightness":42,"brightness":43'),
    EVENT.replace('"brightness":42', '"brightness":' + '[' * 1500 + '0' + ']' * 1500),
    ACK, 'null', b'{}', ' ' * 65537, '{',
])
@pytest.mark.tc027_02
def test_event_protocol_is_fail_closed(monkeypatch, message):
    async def scenario():
        socket = Socket(AUTH + [ACK, message])
        fake(monkeypatch, [socket])
        delivered = []

        async def callback(event):
            delivered.append(event)

        client = runtime().HAStateSubscriptionClient(configuration(), callback)
        await finish(client)
        assert client.subscription_health().reason == "protocol_error"
        assert not client.subscription_health().subscribed
        assert delivered == [] and socket.closed == 1
        await client.aclose()
    asyncio.run(scenario())


@pytest.mark.tc027_02
def test_ordered_backpressure_and_null_removed_state(monkeypatch):
    async def scenario():
        removed = EVENT.replace('"old_state":null', '"old_state":{}').replace(
            '"new_state":{"state":"on","attributes":{"brightness":42}}', '"new_state":null')
        socket = Socket(AUTH + [ACK, EVENT, removed])
        fake(monkeypatch, [socket])
        entered, release = asyncio.Event(), asyncio.Event()
        delivered = []
        active = 0

        async def callback(event):
            nonlocal active
            active += 1
            assert active == 1
            delivered.append(copy.deepcopy(event))
            if len(delivered) == 1:
                entered.set()
                await release.wait()
            event.clear()  # Consumer mutation cannot change health or later events.
            active -= 1

        client = runtime().HAStateSubscriptionClient(configuration(), callback)
        running = asyncio.create_task(client.run())
        try:
            await entered.wait()
            assert len(socket.messages) == 1 and len(delivered) == 1
            assert client.subscription_health().subscribed
            stable = client.subscription_health()
            release.set()
            await socket.waiting.wait()
            assert len(delivered) == 2 and active == 0
            assert delivered[0] == json.loads(EVENT)["event"]
            assert delivered[1]["data"]["new_state"] is None
            assert client.subscription_health() is stable
        finally:
            await client.aclose()
            await running
        assert socket.closed == 1
    asyncio.run(scenario())


@pytest.mark.parametrize("mode,reason", [
    ("raise", "delivery_failed"), ("return", "delivery_failed"),
    ("cancel", "delivery_failed"), ("timeout", "delivery_timeout"),
])
@pytest.mark.tc027_02
def test_consumer_failures_terminal_without_retry(monkeypatch, mode, reason):
    async def scenario():
        socket = Socket(AUTH + [ACK, EVENT, EVENT])
        attempts = fake(monkeypatch, [socket])
        cancelled = asyncio.Event()
        calls = []

        def callback(event):
            calls.append(1)
            if mode == "raise":
                raise ValueError("fixture callback secret")
            if mode == "return":
                return None

            async def waiting():
                if mode == "cancel":
                    raise asyncio.CancelledError("fixture callback secret")
                try:
                    await asyncio.Future()
                finally:
                    cancelled.set()
            return waiting()

        client = runtime().HAStateSubscriptionClient(configuration(), callback,
                                                     delivery_timeout_ms=1)
        await finish(client)
        assert client.subscription_health().state == "failed"
        assert client.subscription_health().reason == reason
        assert not client.subscription_health().subscribed
        assert calls == [1] and attempts.attempts == 1
        assert len(socket.messages) == 1 and socket.closed == 1
        if mode == "timeout":
            assert cancelled.is_set()
        await client.aclose()
    asyncio.run(scenario())


@pytest.mark.tc027_03
def test_reconnect_requires_fresh_ack_and_uses_lifetime_budget(monkeypatch):
    async def scenario():
        sockets = [Socket(AUTH + [ACK, EVENT, OSError("lost")]), Socket(AUTH)]
        first, second = sockets
        attempts = fake(monkeypatch, sockets)
        seen = []

        async def callback(event):
            seen.append(event)

        client = runtime().HAStateSubscriptionClient(configuration(attempts=1), callback)
        running = asyncio.create_task(client.run())
        try:
            await second.waiting.wait()
            assert len(seen) == 1
            assert client.health().state == "connected"
            assert client.health().reconnect_attempt == 1
            assert client.subscription_health().state == "subscribing"
            assert not client.subscription_health().subscribed
            assert first.closed == 1
            assert first.sent[1:] == second.sent[1:] == [COMMAND]
            assert attempts.attempts == 2 and attempts.delays == [.01]
        finally:
            await client.aclose()
            await running
        assert second.closed == 1
    asyncio.run(scenario())


@pytest.mark.parametrize("acknowledged", [False, True])
@pytest.mark.tc027_03
def test_flapping_exhausts_without_budget_reset(monkeypatch, acknowledged):
    async def scenario():
        peers = [Socket(AUTH + ([ACK] if acknowledged else []) + [OSError("lost")])
                 for _ in range(3)]
        originals = peers[:]
        attempts = fake(monkeypatch, peers)
        client = runtime().HAStateSubscriptionClient(configuration(attempts=2), consume)
        await finish(client)
        assert attempts.attempts == 3 and attempts.delays == [.01, .02]
        assert client.subscription_health().state == "failed"
        assert client.subscription_health().reason == "reconnect_exhausted"
        assert all(peer.closed == 1 and peer.sent[1:] == [COMMAND] for peer in originals)
        await client.aclose()
    asyncio.run(scenario())


@pytest.mark.tc027_03
def test_ack_timeout_retries_boundedly(monkeypatch):
    async def scenario():
        peers = [Socket(AUTH), Socket(AUTH)]
        originals = peers[:]
        attempts = fake(monkeypatch, peers)
        client = runtime().HAStateSubscriptionClient(configuration(timeout=10, attempts=1), consume)
        await finish(client)
        assert client.subscription_health().reason == "reconnect_exhausted"
        assert attempts.attempts == 2
        assert all(peer.closed == 1 and peer.sent[1:] == [COMMAND] for peer in originals)
        await client.aclose()
    asyncio.run(scenario())


@pytest.mark.parametrize("cancel_run", [False, True])
@pytest.mark.tc027_03
def test_shutdown_cancels_delivery_before_second_event(monkeypatch, cancel_run):
    async def scenario():
        socket = Socket(AUTH + [ACK, EVENT, EVENT])
        fake(monkeypatch, [socket])
        entered, cancelled = asyncio.Event(), asyncio.Event()
        calls = []

        async def callback(event):
            calls.append(1)
            entered.set()
            try:
                await asyncio.Future()
            finally:
                cancelled.set()

        client = runtime().HAStateSubscriptionClient(configuration(), callback)
        running = asyncio.create_task(client.run())
        await entered.wait()
        if cancel_run:
            running.cancel()
            with pytest.raises(asyncio.CancelledError):
                await running
            assert client.subscription_health().reason == "cancelled"
        else:
            await asyncio.gather(client.aclose(), client.aclose())
            await running
        assert cancelled.is_set() and calls == [1] and len(socket.messages) == 1
        assert socket.closed == 1
        await client.aclose()
        frozen = client.subscription_health()
        await client.aclose()
        assert client.subscription_health() is frozen and frozen.state == "closed"
        assert not [t for t in asyncio.all_tasks() if t is not asyncio.current_task()
                    and t.get_name().startswith("ha-websocket-")]
    asyncio.run(scenario())


@pytest.mark.tc027_03
def test_cancelled_close_waiter_preserves_owned_cleanup(monkeypatch):
    async def scenario():
        closing, release = asyncio.Event(), asyncio.Event()

        async def slow_close():
            closing.set()
            await release.wait()

        socket = Socket(AUTH + [ACK], close=slow_close)
        fake(monkeypatch, [socket])
        client = runtime().HAStateSubscriptionClient(configuration(), consume)
        running = asyncio.create_task(client.run())
        await socket.waiting.wait()
        waiter = asyncio.create_task(client.aclose())
        await closing.wait()
        frozen = client.subscription_health()
        assert frozen.state == "closed" and not frozen.subscribed
        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter
        release.set()
        await client.aclose()
        await running
        assert client.subscription_health() is frozen and socket.closed == 1
    asyncio.run(scenario())


@pytest.mark.tc027_03
def test_close_before_run_and_cross_loop():
    client = runtime().HAStateSubscriptionClient(configuration(), consume)
    asyncio.run(client.aclose())
    assert client.subscription_health().state == "closed"
    with pytest.raises(RuntimeError, match="^wrong_event_loop$"):
        asyncio.run(client.aclose())
    with pytest.raises(RuntimeError, match="^wrong_event_loop$"):
        asyncio.run(client.run())


@pytest.mark.parametrize("consumer_failure", [False, True])
@pytest.mark.tc027_04
def test_redacted_diagnostics_and_serialization(monkeypatch, caplog, consumer_failure):
    async def scenario():
        token = "fictional-websocket-credential-7249"
        frames = [ACK, EVENT] if consumer_failure else [
            '{"id":1,"type":"result","success":false,'
            '"error":{"code":"' + token + '","message":"' + token + '"}}']
        socket = Socket(AUTH + frames)
        fake(monkeypatch, [socket])

        async def callback(event):
            raise ValueError(token)

        client = runtime().HAStateSubscriptionClient(configuration(), callback)
        with caplog.at_level(logging.DEBUG):
            await finish(client)
            await client.aclose()
        diagnostics = repr(client) + repr(client.subscription_health())
        diagnostics += json.dumps(client.subscription_health().to_dict()) + caplog.text
        assert token not in diagnostics and "fixture.invalid" not in diagnostics
        assert "access_token" not in caplog.text
        for operation in (pickle.dumps, copy.copy, copy.deepcopy):
            with pytest.raises(TypeError, match="^client_serialization_refused$"):
                operation(client)
    asyncio.run(scenario())


@pytest.mark.tc027_03
def test_close_from_consumer_fails_without_self_join(monkeypatch):
    async def scenario():
        socket = Socket(AUTH + [ACK, EVENT])
        fake(monkeypatch, [socket])
        observed = []

        async def callback(event):
            try:
                await client.aclose()
            except RuntimeError as error:
                observed.append(str(error))
                raise

        client = runtime().HAStateSubscriptionClient(configuration(), callback)
        await finish(client)
        assert observed == ["close_from_consumer"]
        assert client.subscription_health().reason == "delivery_failed" and socket.closed == 1
        await client.aclose()
    asyncio.run(scenario())


@pytest.mark.tc027_04
@pytest.mark.ha_websocket_wire
def test_production_loopback_subscription(caplog):
    # Standalone artifact smoke exercises the actual installed/public API with
    # explicit require() checks that also remain active under optimized Python.
    from ha_subscription_artifact_smoke import check

    async def bounded_check():
        return await asyncio.wait_for(check(), 15)

    with caplog.at_level(logging.DEBUG):
        report = asyncio.run(bounded_check())
    assert "fictional-installed-subscription-token" not in caplog.text
    assert "access_token" not in caplog.text
    assert report["connections"] == 3 and report["delivered"] == 2
    assert report["active_after_close"] == 0


@pytest.mark.tc027_04
@pytest.mark.ha_websocket_wire
def test_loopback_failed_readiness_assertion_drains_peer(monkeypatch):
    from ha_subscription_artifact_smoke import check

    mod = runtime()
    original = mod.HAStateSubscriptionClient.subscription_health

    def premature_readiness(client):
        snapshot = original(client)
        if snapshot.state == "subscribing":
            return mod.HASubscriptionHealth("subscribed")
        return snapshot

    monkeypatch.setattr(mod.HAStateSubscriptionClient, "subscription_health", premature_readiness)

    async def scenario():
        # Force failure while the real peer is waiting on its ACK-release gate.
        # A timeout is a test failure, never evidence of a detected regression.
        with pytest.raises(RuntimeError, match="^installed_subscription_check_failed$"):
            await asyncio.wait_for(check(), 15)
        assert not [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]

    asyncio.run(scenario())


@pytest.mark.parametrize("mode", ["supervisor", "child_close"])
@pytest.mark.tc027_03
def test_consumer_shutdown_coordination_is_bounded(monkeypatch, mode):
    async def scenario():
        socket = Socket(AUTH + [ACK, EVENT])
        fake(monkeypatch, [socket])
        stop = asyncio.Event()
        cancelled, calls = [], []

        async def callback(event):
            calls.append(1)
            if mode == "supervisor":
                stop.set()  # Return to the reader; do not await its shutdown.
                return
            try:
                await asyncio.create_task(client.aclose())
            except asyncio.CancelledError:
                cancelled.append(True)
                raise

        async def supervisor():
            await stop.wait()
            await client.aclose()

        client = runtime().HAStateSubscriptionClient(configuration(), callback)
        closer = asyncio.create_task(supervisor()) if mode == "supervisor" else None
        try:
            await asyncio.wait_for(client.run(), 3)
            if closer is not None:
                await asyncio.wait_for(closer, 3)
        finally:
            if closer is not None and not closer.done():
                closer.cancel()
                await asyncio.gather(closer, return_exceptions=True)
            await client.aclose()
        assert calls == [1] and socket.closed == 1
        assert cancelled == ([True] if mode == "child_close" else [])
        assert client.subscription_health().state == "closed"
        assert not [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]

    asyncio.run(scenario())


@pytest.mark.tc027_02
def test_callback_timeout_exception_is_consumer_failure(monkeypatch):
    async def scenario():
        socket = Socket(AUTH + [ACK, EVENT])
        fake(monkeypatch, [socket])

        async def callback(event):
            raise TimeoutError("private consumer detail")

        client = runtime().HAStateSubscriptionClient(configuration(), callback)
        await finish(client)
        assert client.subscription_health().reason == "delivery_failed"
        await client.aclose()
    asyncio.run(scenario())


@pytest.mark.tc027_03
def test_late_consumer_cannot_reopen_closed_health(monkeypatch):
    async def scenario():
        socket = Socket(AUTH + [ACK, EVENT, EVENT])
        fake(monkeypatch, [socket])
        entered, cancelled, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
        calls = []

        async def callback(event):
            calls.append(1)
            entered.set()
            try:
                await asyncio.Future()
            except asyncio.CancelledError:
                cancelled.set()
                await release.wait()
                raise ValueError("late private consumer failure")

        client = runtime().HAStateSubscriptionClient(configuration(), callback)
        running = asyncio.create_task(client.run())
        await entered.wait()
        closing = asyncio.create_task(client.aclose())
        await cancelled.wait()
        frozen = client.subscription_health()
        assert frozen.state == "closed" and not frozen.subscribed and not closing.done()
        release.set()
        await closing
        await running
        assert client.subscription_health() is frozen
        assert calls == [1] and socket.closed == 1
    asyncio.run(scenario())


@pytest.mark.tc027_03
def test_auth_rejection_never_subscribes(monkeypatch):
    async def scenario():
        socket = Socket(['{"type":"auth_required"}', '{"type":"auth_invalid"}'])
        attempts = fake(monkeypatch, [socket])
        client = runtime().HAStateSubscriptionClient(configuration(), consume)
        await finish(client)
        assert client.health().state == "auth_failed"
        assert client.subscription_health().state == "failed"
        assert client.subscription_health().reason == "auth_failed"
        assert not client.subscription_health().subscribed
        assert len(socket.sent) == 1 and attempts.attempts == 1 and socket.closed == 1
        await client.aclose()
    asyncio.run(scenario())


@pytest.mark.tc027_03
def test_process_control_failure_propagates_after_cleanup(monkeypatch):
    class StopConsumer(BaseException):
        pass

    async def scenario():
        socket = Socket(AUTH + [ACK, EVENT])
        fake(monkeypatch, [socket])

        async def callback(event):
            raise StopConsumer()

        client = runtime().HAStateSubscriptionClient(configuration(), callback)
        with pytest.raises(StopConsumer):
            await finish(client)
        assert socket.closed == 1
        assert client.subscription_health().state == "failed"
        assert not client.subscription_health().subscribed
        await client.aclose()
    asyncio.run(scenario())
