"""Generator verification for REQ-036; independent TC approval remains pending."""

import copy
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from home_device_fabric.ha_discovery import HADiscoveryError, HADiscoverySnapshot
from home_device_fabric.ha_mapping import HAMappingError, HARegistryMapper
from home_device_fabric.reconciliation import ReconciliationError, ReconnectReconciler
from home_device_fabric.state_store import CurrentStateStore, StateStoreError
from state_schema.canonical_state import StateCollection
from state_store_artifact_smoke import configuration, context, snapshot

HOME = "home-example"
T = "2026-10-30T10:00:00Z"


def source(value="on", time=T):
    return {
        "devices": [],
        "areas": [],
        "entities": [{"entity_id": "switch.example"}],
        "states": [
            {"entity_id": "switch.example", "state": value, "attributes": {}, "last_updated": time}
        ],
    }


def mapped(data):
    return HARegistryMapper(
        {
            "schema_version": 1,
            "home": configuration()["inventories"][0]["home"],
            "provider_instance_id": "ha-example",
            "area_ids": {},
            "device_ids": {},
            "entity_ids": {"switch.example": "device-one"},
        }
    ).map(data)


def discovery(data):
    labels = ("devices", "entities", "areas", "states")
    return HADiscoverySnapshot(
        tuple(json.dumps(data[k]) for k in labels), tuple(len(data[k]) for k in labels)
    )


def current(store):
    return StateCollection(
        1,
        tuple(v.state for v in store.snapshot(context(), home_id=HOME, now_ms=100, max_age_ms=100)),
    )


def coordinator(store, **changes):
    return ReconnectReconciler(
        **{
            "store": store,
            "write_context": context(),
            "registered_inventory": configuration()["inventories"][0],
            "provider_instance_id": "ha-example",
            "profiles": [{"entity_id": "switch.example", "kind": "switch"}],
            "max_buffer_events": 10,
            "max_input_bytes": 100000,
            **changes,
        }
    )


def envelope(time, value=False, ordinal=1, entity="switch.example", device="device-one"):
    from home_device_fabric.ha_normalization import _timestamp

    normalized_time = _timestamp(time)
    delta = snapshot(device=device, value=value)
    delta["availability"]["observed_at"] = normalized_time
    delta["reported_state"]["is_on"]["observed_at"] = normalized_time
    return {
        "normalized_delta": delta,
        "source_entity_id": entity,
        "original_ordering": {"epoch": 1, "sequence": 1},
        "observed_at": time,
        "capture_ordinal": ordinal,
    }


def run(store, data=None, engine=None, **changes):
    data = source() if data is None else data
    try:
        mapping = mapped(data)
    except HAMappingError as error:
        mapping = error
    return (engine or coordinator(store)).reconcile(
        **{
            "home_id": HOME,
            "epoch": 2,
            "attempt_number": 1,
            "max_attempts": 3,
            "discovery_result": discovery(data),
            "mapping_result": mapping,
            "buffered_events": [],
            "current_states": current(store),
            "now_ms": 100,
            **changes,
        }
    )


def view(store, device="device-one", home=HOME):
    return store.read(context(home), home_id=home, device_id=device, now_ms=100, max_age_ms=100)


@pytest.fixture
def store():
    return CurrentStateStore(**configuration())


@pytest.mark.parametrize(
    "time,expected,count",
    [
        ("2026-10-30T09:59:00Z", True, 0),
        (T, True, 0),
        ("2026-10-30T11:00:00+01:00", True, 0),
        ("2026-10-30T10:00:00.000001Z", False, 1),
    ],
)
def test_snapshot_time_filters_before_rebase(store, time, expected, count):
    result = run(store, buffered_events=[envelope(time)])
    assert result.outcome == "reconciled" and result.buffered_event_count == count
    state = view(store).state.to_dict()
    assert state["reported_state"]["is_on"]["value"] is expected
    assert state["availability"]["ordering"] == {"epoch": 2, "sequence": count}
    assert view(store).revision == view(store, "device-two").revision == 1
    assert view(store, "device-two").state.reported_state == ()


def test_dedup_and_sequence_rebase_are_detached(store):
    first = envelope("2026-10-30T10:01:00Z")
    duplicate = {**copy.deepcopy(first), "capture_ordinal": 2}
    before = copy.deepcopy([first, duplicate])
    result = run(store, buffered_events=[first, duplicate])
    assert result.buffered_event_count == 1 and [first, duplicate] == before
    assert view(store).state.availability.ordering.sequence == 1
    exported = result.to_dict()
    exported["outcome"] = "changed"
    assert result.outcome == "reconciled"


@pytest.mark.parametrize("kind", ["unavailable", "missing", "removed", "unknown"])
def test_projection_and_intent_preservation(store, kind):
    seed = snapshot(value=False)
    seed["reported_state"]["old_member"] = copy.deepcopy(seed["reported_state"]["is_on"])
    seed["desired_state"] = {"revision": 1, "values": {"is_on": True}, "report_baseline": None}
    store.put(
        context(), home_id=HOME, device_id="device-one", state=seed, expected_revision=0, now_ms=90
    )
    data = source(kind)
    if kind == "missing":
        data["states"] = []
    if kind == "removed":
        data["entities"] = []
    assert run(store, data).outcome == "reconciled"
    state = view(store).state.to_dict()
    assert state["desired_state"] == seed["desired_state"]
    if kind == "removed":
        assert state["reported_state"] == {} and state["availability"]["status"] == "unknown"
    elif kind == "unknown":
        assert state["reported_state"]["is_on"]["value"] is None
        assert "old_member" not in state["reported_state"]
    else:
        assert state["reported_state"]["is_on"]["value"] is False
        assert state["availability"]["status"] == (
            "offline" if kind == "unavailable" else "unknown"
        )


def test_missing_row_replays_but_removed_or_remapped_entity_does_not(store):
    data = source()
    data["states"] = []
    assert run(store, data, buffered_events=[envelope(T)]).buffered_event_count == 1
    data["entities"] = []
    assert run(store, data, epoch=3, buffered_events=[envelope(T)]).buffered_event_count == 0
    assert view(store).state.reported_state == ()
    assert (
        run(
            store, epoch=4, buffered_events=[envelope("2026-10-30T10:01:00Z", device="device-two")]
        ).buffered_event_count
        == 0
    )


def test_repeat_reconnect_replaces_and_retains_current_intent_at_lock(store):
    assert run(store).outcome == "reconciled"
    prior = current(store)
    seed = view(store).state.to_dict()
    seed["desired_state"] = {"revision": 3, "values": {"is_on": False}, "report_baseline": None}
    store.put(
        context(), home_id=HOME, device_id="device-one", state=seed, expected_revision=1, now_ms=100
    )
    assert run(store, source("off"), epoch=3, current_states=prior).outcome == "reconciled"
    assert view(store).state.desired_state.revision == 3
    assert view(store).revision == 3 and view(store, "device-two").revision == 2


@pytest.mark.parametrize(
    "changes,code",
    [
        ({"epoch": True}, "invalid_input"),
        ({"attempt_number": 0}, "invalid_input"),
        ({"max_attempts": 0}, "invalid_input"),
        ({"now_ms": -1}, "invalid_input"),
        ({"home_id": "home-other"}, "invalid_input"),
    ],
)
def test_invalid_admission_does_not_mark_stale(store, changes, code):
    assert run(store, **changes).failure_code == code
    assert view(store).freshness == "uninitialized" and view(store).revision == 0


@pytest.mark.parametrize("change", ["time", "identity", "ordering", "ordinal", "extra", "intent"])
def test_invalid_envelope_fails_without_partial_publication(store, change):
    event = envelope("2026-10-30T10:01:00Z")
    if change == "time":
        event["observed_at"] = "secret-invalid-time"
    elif change == "identity":
        event["normalized_delta"]["home_id"] = "home-other"
    elif change == "ordering":
        event["original_ordering"]["sequence"] = 3
    elif change == "ordinal":
        event["capture_ordinal"] = True
    elif change == "intent":
        event["normalized_delta"]["desired_state"] = {
            "revision": 1,
            "values": {"is_on": True},
            "report_baseline": None,
        }
    else:
        event["secret-key"] = "secret-value"
    result = run(store, buffered_events=[event])
    assert result.outcome == "terminal_failure" and result.state_stale
    assert view(store).revision == 0 and view(store).state.reported_state == ()
    assert "secret" not in repr(result) + json.dumps(result.to_dict())


@pytest.mark.parametrize("attempt,outcome", [(1, "retryable_failure"), (3, "exhausted_failure")])
def test_retry_ownership_and_recovery(store, attempt, outcome):
    result = run(
        store,
        discovery_result=HADiscoveryError("timeout"),
        mapping_result=None,
        attempt_number=attempt,
    )
    assert result.outcome == outcome and result.state_stale and view(store).freshness == "stale"
    assert view(store).revision == 0 and view(store).updated_at_ms is None
    assert run(store, epoch=4).outcome == "reconciled"
    assert view(store).freshness == "fresh"


def test_retry_refilters_original_events_against_fresh_snapshot(store):
    events = [envelope("2026-10-30T10:01:00Z")]
    before = copy.deepcopy(events)
    assert (
        run(
            store,
            discovery_result=HADiscoveryError("timeout"),
            mapping_result=None,
            buffered_events=events,
        ).outcome
        == "retryable_failure"
    )
    assert (
        run(
            store,
            source(time="2026-10-30T10:02:00Z"),
            epoch=3,
            attempt_number=2,
            buffered_events=events,
        ).buffered_event_count
        == 0
    )
    assert events == before and dict(view(store).state.reported_state)["is_on"].value is True


@pytest.mark.parametrize(
    "mode,code",
    [
        ("duplicate", "projection_failed"),
        ("time", "projection_failed"),
        ("error", "projection_failed"),
        ("capacity", "buffer_overflow"),
        ("bytes", "invalid_input"),
        ("multi", "projection_failed"),
        ("mapping", "mapping_mismatch"),
    ],
)
def test_failures_are_bounded_and_stale(store, mode, code):
    data, changes = source(), {}
    engine = coordinator(store, max_buffer_events=1, max_input_bytes=100000)
    if mode == "duplicate":
        data["states"] *= 2
    elif mode == "time":
        del data["states"][0]["last_updated"]
    elif mode == "error":
        changes["mapping_result"] = HAMappingError("invalid_discovery")
    elif mode == "capacity":
        changes["buffered_events"] = [envelope(T), envelope(T, ordinal=2)]
    elif mode == "bytes":
        engine = coordinator(store, max_input_bytes=1)
    elif mode in ("multi", "mapping"):
        from home_device_fabric.ha_mapping import HAMappingResult

        good = mapped(data)
        raw = good.for_adapter()
        if mode == "multi":
            raw["bindings"]["bindings"][0]["mapping"]["entity_ids"].append("switch.other")
        else:
            raw["inventory"]["devices"][0]["id"] = "device-absent"
            raw["bindings"]["bindings"][0]["device_id"] = "device-absent"
        changes["mapping_result"] = HAMappingResult(
            json.dumps(raw["inventory"]), json.dumps(raw["bindings"]), good._counts
        )
    result = run(store, data, engine=engine, **changes)
    assert result.failure_code == code and result.state_stale
    assert view(store).revision == view(store, "device-two").revision == 0
    assert view(store, home="home-other").freshness == "uninitialized"


def publication(store, epoch=2, events=None, states=None):
    baseline = [snapshot(device=d) for d in ("device-one", "device-two")]
    for state in baseline:
        state["availability"]["ordering"] = {"epoch": epoch, "sequence": 0}
        state["reported_state"]["is_on"]["ordering"] = {"epoch": epoch, "sequence": 0}
    return store.reconcile_home(
        context(),
        home_id=HOME,
        epoch=epoch,
        baseline_states={"schema_version": 1, "states": baseline if states is None else states},
        buffered_events=[] if events is None else events,
        now_ms=100,
    )


@pytest.mark.parametrize("epoch", [1, 2])
def test_epoch_rejection_preserves_entire_publication(store, epoch):
    publication(store)
    before = current(store).to_dict()
    with pytest.raises(StateStoreError, match="epoch_regression"):
        publication(store, epoch)
    assert current(store).to_dict() == before and view(store).revision == 1
    assert publication(store, 3) == 3


def test_stored_order_floor_includes_intent_and_stale_is_persistent(store):
    seed = snapshot()
    seed["desired_state"] = {
        "revision": 1,
        "values": {"is_on": True},
        "report_baseline": {"epoch": 4, "sequence": 0},
    }
    store.put(
        context(), home_id=HOME, device_id="device-one", state=seed, expected_revision=0, now_ms=100
    )
    store.mark_home_stale(context(), home_id=HOME)
    store.mark_home_stale(context(), home_id=HOME)
    assert view(store).freshness == view(store, "device-two").freshness == "stale"
    with pytest.raises(StateStoreError, match="epoch_regression"):
        publication(store, 4)
    assert view(store).revision == 1 and view(store).freshness == "stale"
    publication(store, 5)
    assert view(store).freshness == "fresh" and view(store).state.desired_state.revision == 1


def test_atomic_failure_on_late_invalid_event_or_incomplete_baseline(store):
    good = snapshot()
    good["availability"]["ordering"] = good["reported_state"]["is_on"]["ordering"] = {
        "epoch": 2,
        "sequence": 1,
    }
    bad = copy.deepcopy(good)
    bad["reported_state"]["is_on"]["value"] = True
    for kwargs in ({"events": [good, bad]}, {"states": []}):
        with pytest.raises(StateStoreError):
            publication(store, **kwargs)
        assert view(store).revision == 0 and view(store).freshness == "uninitialized"
    publication(store)


def test_atomic_snapshots_racing_repeated_publications(store):
    barrier = Barrier(2)

    def publish():
        barrier.wait()
        for epoch in range(2, 52):
            publication(store, epoch)

    def observe():
        barrier.wait()
        for _ in range(100):
            rows = store.snapshot(context(), home_id=HOME, now_ms=100, max_age_ms=100)
            assert rows[0].revision == rows[1].revision
            assert rows[0].updated_at_ms == rows[1].updated_at_ms

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(publish), pool.submit(observe)]
        for future in futures:
            future.result()


def test_unauthorized_store_extensions_and_constructor(store):
    with pytest.raises(ReconciliationError):
        coordinator(store, write_context=context(member="member-reader"))
    with pytest.raises(StateStoreError, match="forbidden"):
        store.mark_home_stale(context(member="member-reader"), home_id=HOME)
    with pytest.raises(StateStoreError, match="forbidden"):
        store.reconcile_home(
            context(member="member-reader"),
            home_id=HOME,
            epoch=False,
            baseline_states={},
            buffered_events=[],
            now_ms=False,
        )
    assert view(store).freshness == "uninitialized"


def test_stale_write_failure_does_not_claim_stale():
    class BrokenStore(CurrentStateStore):
        def mark_home_stale(self, *args, **kwargs):
            raise RuntimeError("secret")

    store = BrokenStore(**configuration())
    result = run(store, discovery_result=HADiscoveryError("timeout"), mapping_result=None)
    assert result.failure_code == "stale_mark_failed" and not result.state_stale
    assert view(store).freshness == "uninitialized"


def test_store_failure_never_claims_success():
    class BrokenStore(CurrentStateStore):
        def reconcile_home(self, *args, **kwargs):
            raise RuntimeError("secret")

    store = BrokenStore(**configuration())
    result = run(store)
    assert result.outcome == "retryable_failure" and result.failure_code == "store_failure"
    assert result.state_stale and view(store).revision == 0


def test_offline_no_ambient_effects(store, offline):
    assert run(store).outcome == "reconciled"
    assert offline == []


def test_smoke_contract_under_offline_guard(offline):
    from reconciliation_artifact_smoke import check
    assert check() == {"checks": 13, "offline": True}
    assert offline == []
