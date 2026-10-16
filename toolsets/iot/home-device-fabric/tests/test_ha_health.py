"""Proposed REQ-026 literal health expectations; controlled clocks and peers."""

import asyncio
import importlib
import json
import pickle
from dataclasses import FrozenInstanceError

import pytest

pytestmark = pytest.mark.ha_websocket_async
TOKEN = "fictional-health-token-4672"
URL = "http://fixture.invalid:8123"


@pytest.fixture(autouse=True)
def load_runtime():
    global mod, HAConfiguration, HARestError, HARuntimeInfo, HAConnectionHealth
    mod = importlib.import_module("home_device_fabric.ha_health")
    HAConfiguration = importlib.import_module("home_device_fabric.ha_configuration").HAConfiguration
    rest = importlib.import_module("home_device_fabric.ha_rest")
    HARestError, HARuntimeInfo = rest.HARestError, rest.HARuntimeInfo
    socket = importlib.import_module("home_device_fabric.ha_websocket")
    HAConnectionHealth = socket.HAConnectionHealth


def configuration(token=TOKEN, url=URL):
    return HAConfiguration({"schema_version": 1, "base_url": url,
                            "request_timeout_ms": 1000, "reconnect_max_attempts": 1,
                            "reconnect_initial_delay_ms": 10}, access_token=token)


async def settle(predicate):
    for _ in range(200):
        if predicate():
            return
        await asyncio.sleep(0)
    raise AssertionError("expected state did not arrive")


def run_scenario(scenario, peers):
    """Bound waits and release fake gates even when a lifecycle assertion fails."""
    async def bounded():
        try:
            try:
                await asyncio.wait_for(scenario(), timeout=3)
            except TimeoutError:
                pytest.fail("health scenario exceeded its three-second deadline")
        finally:
            rest, _, clock = peers
            if rest.release_cancel is not None:
                rest.release_cancel.set()
            # A broken late-result guard can leave a probe asleep on fake time.
            await clock.advance(1000)
            tasks = [task for task in asyncio.all_tasks()
                     if task is not asyncio.current_task()]
            for task in tasks:
                task.cancel()
            if tasks:
                _, pending = await asyncio.wait(tasks, timeout=1)
                assert not pending, "health scenario cleanup did not drain"
    asyncio.run(bounded())


class Clock:
    def __init__(self):
        self.now = 100.0
        self.waits = []

    async def sleep(self, delay):
        if delay <= 0:
            await asyncio.sleep(0)
            return
        future = asyncio.get_running_loop().create_future()
        self.waits.append((self.now + delay, future))
        await future

    async def advance(self, seconds):
        self.now += seconds
        for deadline, future in self.waits:
            if deadline <= self.now and not future.done():
                future.set_result(None)
        for _ in range(20):
            await asyncio.sleep(0)


class Rest:
    def __init__(self):
        self.calls = []
        self.active = 0
        self.max_active = 0
        self.closed = 0
        self.release_cancel = None

    async def runtime_info(self, *, correlation_id):
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        future = asyncio.get_running_loop().create_future()
        self.calls.append((correlation_id, future))
        try:
            try:
                return await future
            except asyncio.CancelledError:
                if self.release_cancel is None:
                    raise
                await self.release_cancel.wait()
                return HARuntimeInfo("late-fixture-version")
        finally:
            self.active -= 1

    def complete(self, error=None):
        identity, future = self.calls[-1]
        if error is None:
            future.set_result(HARuntimeInfo("fixture-version"))
        else:
            future.set_exception(error)

    async def aclose(self):
        self.closed += 1


class Socket:
    def __init__(self):
        self.value = HAConnectionHealth()
        self.starts = 0
        self.closed = 0
        self.stop = None

    def health(self):
        return self.value

    def transition(self, state, reason=None, attempt=0):
        self.value = HAConnectionHealth(state, reason, attempt, self.value.sequence + 1)

    async def run(self):
        self.starts += 1
        if self.stop:
            raise self.stop
        await asyncio.Future()

    async def aclose(self):
        self.closed += 1
        self.transition("closed")


@pytest.fixture
def peers(monkeypatch):
    rest, socket, clock = Rest(), Socket(), Clock()
    monkeypatch.setattr(mod, "HARestClient", lambda config: rest)
    monkeypatch.setattr(mod, "HAWebSocketClient", lambda config: socket)
    monkeypatch.setattr(mod, "_clock", lambda: clock.now)
    monkeypatch.setattr(mod, "_sleep", clock.sleep)
    return rest, socket, clock


@pytest.mark.tc026_01
@pytest.mark.ha_websocket_pure
def test_no_io_initial_immutable_and_redacted(peers):
    rest, socket, _ = peers
    client = mod.HAHealthMonitor(configuration())
    original = client.health()
    assert original.to_dict() == {
        "state": "disconnected", "rest_state": "unknown", "rest_reason": None,
        "rest_reachable": None, "event_stream_connected": False,
        "websocket": {"state": "disconnected", "reason": None,
                      "reconnect_attempt": 0, "sequence": 0},
        "closed": False, "sequence": 0}
    assert rest.calls == [] and socket.starts == 0
    exported = original.to_dict()
    exported['websocket']['state'] = 'connected'
    assert client.health() == original and client.health().websocket.state == "disconnected"
    with pytest.raises(FrozenInstanceError):
        original.sequence = 20
    with pytest.raises(RuntimeError, match="client_initialized"):
        client.__init__(configuration())
    for value in (client, original, exported):
        assert TOKEN not in repr(value) and URL not in repr(value)
    for operation in (pickle.dumps, lambda value: value.__getstate__()):
        with pytest.raises(TypeError, match="client_serialization_refused"):
            operation(client)


@pytest.mark.tc026_01
@pytest.mark.ha_websocket_pure
@pytest.mark.parametrize("interval", [True, False, 0, -1, 60001, 1.5, "10", None])
def test_interval_rejected_before_children(monkeypatch, interval):
    def unexpected(*args):
        raise AssertionError("child constructed")
    monkeypatch.setattr(mod, "HARestClient", unexpected)
    with pytest.raises(ValueError, match="^invalid_observation_interval$"):
        mod.HAHealthMonitor(configuration(), observation_interval_ms=interval)


@pytest.mark.tc026_01
@pytest.mark.ha_websocket_pure
@pytest.mark.parametrize("config", [None, {}, "private-endpoint", 1])
def test_configuration_rejected(config):
    with pytest.raises(TypeError, match="^invalid_configuration$"):
        mod.HAHealthMonitor(config)


@pytest.mark.tc026_01
@pytest.mark.ha_websocket_pure
@pytest.mark.parametrize("rest,ws,expected", [
    ("unknown", "connected", "disconnected"),
    ("reachable", "connected", "connected"),
    ("unreachable", "connected", "disconnected"),
    ("reachable", "disconnected", "disconnected"),
    ("reachable", "connecting", "disconnected"),
    ("reachable", "authenticating", "disconnected"),
    ("reachable", "failed", "disconnected"),
    ("reachable", "closed", "disconnected"),
    ("reachable", "reconnecting", "reconnecting"),
    ("unknown", "reconnecting", "reconnecting"),
    ("auth_failed", "reconnecting", "auth_failed"),
    ("auth_failed", "connected", "auth_failed"),
    ("reachable", "auth_failed", "auth_failed"),
])
def test_literal_state_priority(rest, ws, expected):
    snapshot = mod.HAIntegrationHealth(rest, "auth_failed" if rest == "auth_failed" else None,
                                       HAConnectionHealth(ws))
    assert snapshot.state == expected
    assert snapshot.event_stream_connected == (ws == "connected")
    assert snapshot.rest_reachable == (None if rest == "unknown" else rest == "reachable")
    closed = mod.HAIntegrationHealth(snapshot.rest_state, snapshot.rest_reason,
                                     snapshot.websocket, True, 1)
    assert closed.state == "closed" and not closed.event_stream_connected
    assert closed.rest_reachable is None


@pytest.mark.tc026_01
@pytest.mark.ha_websocket_pure
@pytest.mark.parametrize("kwargs", [
    {"rest_state": "private-text"}, {"rest_reason": "private-text"},
    {"rest_reason": []}, {"websocket": {}}, {"closed": 1}, {"sequence": True},
    {"sequence": -1}, {"rest_state": "reachable", "rest_reason": "timeout"},
    {"rest_state": "auth_failed"}, {"rest_reason": "auth_failed"},
])
def test_invalid_snapshot_rejected(kwargs):
    with pytest.raises(ValueError, match="^invalid_integration_health$"):
        mod.HAIntegrationHealth(**kwargs)


@pytest.mark.tc026_02
def test_independent_failure_recovery_sampling_and_stale_success(peers):
    async def scenario():
        rest, socket, clock = peers
        client = mod.HAHealthMonitor(configuration(), observation_interval_ms=100)
        running = asyncio.create_task(client.run())
        await settle(lambda: len(rest.calls) == 1)
        socket.transition("connected")
        assert client.health().rest_reachable is None
        assert client.health().event_stream_connected
        rest.complete()
        await settle(lambda: client.health().state == "connected")
        first = client.health()
        assert client.health() is first  # No sequence growth on unchanged observations.
        socket.transition("reconnecting", "transport_failed", 1)
        await clock.advance(.1)
        assert client._health.websocket.state == "reconnecting"  # Periodic sampler, no health read.
        assert client.health().rest_state == "unknown" and client.health().rest_reason == "stale"
        await settle(lambda: len(rest.calls) == 2)
        rest.complete(HARestError("auth_failed", correlation_id="0", http_status=401))
        await settle(lambda: client.health().state == "auth_failed")
        socket.transition("connected", attempt=1)
        assert client.health().state == "auth_failed"  # REST failure wins.
        await clock.advance(.1)
        await settle(lambda: len(rest.calls) == 3)
        rest.complete()
        await settle(lambda: client.health().state == "connected")
        assert client.health().sequence > first.sequence
        assert first.rest_state == "reachable" and first.websocket.reconnect_attempt == 0
        # A scheduler gap cannot leave stale success visible on the first read.
        clock.now += .101
        assert client.health().rest_reachable is None
        assert client.health().state == "disconnected"
        await client.aclose()
        await running
        assert rest.max_active == 1 and rest.closed == socket.closed == 1
    run_scenario(scenario, peers)


@pytest.mark.tc026_02
@pytest.mark.parametrize("error,reason", [("timeout", "timeout"),
                                        ("transport_failed", "transport_failed"),
                                        ("http_error", "http_error"),
                                        ("invalid_response", "invalid_response"),
                                        ("unexpected", "internal_error")])
def test_rest_errors_are_finite_and_not_socket_failures(peers, error, reason):
    async def scenario():
        rest, socket, _ = peers
        client = mod.HAHealthMonitor(configuration())
        running = asyncio.create_task(client.run())
        await settle(lambda: rest.calls)
        socket.transition("connected")
        failure = (RuntimeError(TOKEN + URL) if error == "unexpected"
                   else HARestError(error, correlation_id="0"))
        rest.complete(failure)
        await settle(lambda: client.health().rest_state == "unreachable")
        assert client.health().rest_reason == reason
        assert client.health().state == "disconnected" and client.health().event_stream_connected
        assert TOKEN not in repr(client.health()) and URL not in repr(client.health())
        await client.aclose()
        await running
    run_scenario(scenario, peers)


@pytest.mark.tc026_02
def test_slow_probe_never_overlaps_or_queues_catchup(peers):
    async def scenario():
        rest, socket, clock = peers
        client = mod.HAHealthMonitor(configuration(), observation_interval_ms=100)
        running = asyncio.create_task(client.run())
        await settle(lambda: rest.calls)
        await clock.advance(10)
        assert len(rest.calls) == 1 and rest.active == 1
        socket.transition("auth_failed", "auth_failed")
        await clock.advance(.1)
        assert client._health.state == "auth_failed"
        rest.complete()
        await settle(lambda: len(rest.calls) == 2)
        assert rest.active == rest.max_active == 1
        await client.aclose()
        await running
        assert socket.starts == 1
    run_scenario(scenario, peers)


@pytest.mark.tc026_03
@pytest.mark.parametrize("token", ["0", "1", "h", TOKEN])
def test_internal_correlation_never_contains_credential(peers, token):
    async def scenario():
        rest, _, _ = peers
        client = mod.HAHealthMonitor(configuration(token=token))
        running = asyncio.create_task(client.run())
        await settle(lambda: rest.calls)
        assert token not in rest.calls[0][0]
        rest.complete()
        await settle(lambda: client.health().rest_reachable is True)
        assert "fixture-version" not in json.dumps(client.health().to_dict())
        await client.aclose()
        await running
    run_scenario(scenario, peers)


@pytest.mark.tc026_04
def test_close_before_start_and_repeated_lifecycle(peers):
    async def scenario():
        rest, socket, _ = peers
        client = mod.HAHealthMonitor(configuration())
        await asyncio.gather(client.aclose(), client.aclose())
        final = client.health()
        await client.aclose()
        assert client.health() is final and final.state == "closed"
        with pytest.raises(RuntimeError, match="client_closed"):
            await client.run()
        assert not rest.calls and socket.starts == 0 and rest.closed == socket.closed == 1
    run_scenario(scenario, peers)


@pytest.mark.tc026_04
@pytest.mark.parametrize("cancel_run", [False, True])
def test_gated_late_result_cannot_change_closed_snapshot(peers, cancel_run):
    async def scenario():
        rest, socket, _ = peers
        rest.release_cancel = asyncio.Event()
        client = mod.HAHealthMonitor(configuration())
        running = asyncio.create_task(client.run())
        await settle(lambda: rest.calls)
        with pytest.raises(RuntimeError, match="client_started"):
            await client.run()
        if cancel_run:
            running.cancel()
            await settle(lambda: client.health().closed)
            running.cancel()
        closing = asyncio.create_task(client.aclose())
        await settle(lambda: client.health().closed)
        frozen = client.health()
        closing.cancel()
        with pytest.raises(asyncio.CancelledError):
            await closing
        socket.transition("connected")
        rest.release_cancel.set()
        # Completion must follow the released late result without advancing
        # fake time: a closed probe must not schedule another interval sleep.
        await settle(lambda: running.done())
        await client.aclose()
        if cancel_run:
            with pytest.raises(asyncio.CancelledError):
                await running
        else:
            await running
        assert client.health() is frozen and not frozen.event_stream_connected
        assert rest.active == 0 and rest.closed == socket.closed == 1
        assert not [task for task in asyncio.all_tasks() if task is not asyncio.current_task()
                    and task.get_name().startswith("ha-health-")]
    run_scenario(scenario, peers)


@pytest.mark.tc026_04
def test_cross_loop_rejected_before_mutation(peers):
    client = mod.HAHealthMonitor(configuration())
    asyncio.run(client.aclose())
    frozen = client.health()
    for operation in (client.aclose, client.run):
        with pytest.raises(RuntimeError, match="wrong_event_loop"):
            asyncio.run(operation())
    assert client.health() is frozen


@pytest.mark.tc026_04
def test_worker_failure_redacted_and_owned_cleanup(peers):
    async def scenario():
        rest, socket, _ = peers
        socket.stop = RuntimeError(TOKEN + URL)
        client = mod.HAHealthMonitor(configuration())
        with pytest.raises(RuntimeError, match="^health_monitor_failed$") as caught:
            await client.run()
        assert caught.value.__context__ is None and caught.value.__cause__ is None
        assert client.health().state == "closed"
        await client.aclose()
        assert rest.closed == socket.closed == 1
    run_scenario(scenario, peers)


@pytest.mark.tc026_03
@pytest.mark.tc026_05
@pytest.mark.ha_websocket_wire
def test_real_loopback_composition():
    from ha_health_artifact_smoke import check
    report = asyncio.run(check())
    assert report["wire_auths"] == 3
    assert report["rest_requests"] >= 3
    assert report["checks"] == ["connected", "independent_rest_auth", "rest_recovery",
                                "finite_socket_reconnect", "terminal_socket_not_restarted",
                                "socket_auth_rejected", "redaction", "closed_snapshot", "drained"]


@pytest.mark.tc026_01
@pytest.mark.ha_websocket_pure
@pytest.mark.parametrize("interval", [1, 60000])
def test_interval_boundaries_and_snapshot_roundtrip(peers, interval):
    client = mod.HAHealthMonitor(configuration(), observation_interval_ms=interval)
    assert pickle.loads(pickle.dumps(client.health())) == client.health()


@pytest.mark.tc026_04
def test_process_control_failure_propagates_after_cleanup(peers):
    class Stop(BaseException):
        pass

    async def scenario():
        rest, socket, _ = peers
        failure = Stop("fixture-control-signal")
        socket.stop = failure
        client = mod.HAHealthMonitor(configuration())
        with pytest.raises(Stop) as caught:
            await client.run()
        assert caught.value is failure
        assert client.health().closed and rest.closed == socket.closed == 1
        await client.aclose()
    run_scenario(scenario, peers)


@pytest.mark.tc026_04
def test_close_before_supervisor_first_instruction_drains_unused_clients(peers):
    async def scenario():
        rest, socket, _ = peers
        client = mod.HAHealthMonitor(configuration())
        running = asyncio.create_task(client.run())
        await asyncio.sleep(0)
        assert client._worker is not None and socket.starts == 0
        await client.aclose()
        await running
        assert client.health().closed and not rest.calls
        assert rest.closed == socket.closed == 1
    run_scenario(scenario, peers)


@pytest.mark.tc026_04
@pytest.mark.parametrize("boundary", ["publish", "sample"])
def test_closed_defense_in_depth_boundaries(peers, monkeypatch, boundary):
    client = mod.HAHealthMonitor(configuration())
    asyncio.run(client.aclose())
    frozen = client.health()
    client._rest_state = "reachable"
    client._rest_reason = None
    client._last_success = 0.0
    if boundary == "publish":
        # Bypass sampling so its independent guard cannot mask publication.
        client._publish()
        assert client.health() is frozen
    else:
        # Observe the sampling boundary before the publication guard can mask it.
        publications = []
        monkeypatch.setattr(mod.HAHealthMonitor, "_publish",
                            lambda self: publications.append(True))
        client._sample()
        assert client._rest_state == "reachable" and client._rest_reason is None
        assert publications == []
        assert client.health() is frozen


@pytest.mark.tc026_04
def test_running_health_requires_owning_loop_even_from_sync_context(peers):
    async def scenario():
        rest, _, _ = peers
        client = mod.HAHealthMonitor(configuration())
        running = asyncio.create_task(client.run())
        await settle(lambda: rest.calls)
        frozen = client._health

        def without_loop():
            with pytest.raises(RuntimeError, match="^wrong_event_loop$") as caught:
                client.health()
            assert caught.value.__context__ is None and caught.value.__cause__ is None

        async def other_loop():
            without_loop()

        await asyncio.to_thread(without_loop)
        await asyncio.to_thread(asyncio.run, other_loop())
        assert client._health is frozen
        await client.aclose()
        await running
    run_scenario(scenario, peers)
