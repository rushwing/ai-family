"""REQ-030 generator probes: explicit epochs and atomic observed deltas."""

import copy
import importlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from threading import Barrier

import pytest
from state_application_artifact_smoke import check, event
from state_store_artifact_smoke import configuration, context

ARGS = {"home_id": "home-example", "device_id": "device-one"}


@pytest.fixture
def api():
    return importlib.import_module("home_device_fabric.state_store")


@pytest.fixture
def store(api):
    result = api.CurrentStateStore(**configuration())
    result.advance_epoch(context(), home_id="home-example", epoch=1)
    return result


def apply(store, data=None, caller=None, **kwargs):
    return store.apply(
        context() if caller is None else caller,
        **{
            **ARGS,
            "now_ms": 100,
            "event": event() if data is None else data,
            **kwargs,
        },
    )


def read(store, **kwargs):
    return store.read(context(), **{**ARGS, "now_ms": 1000, "max_age_ms": 0, **kwargs})


def error(api, code, fn, *args, **kwargs):
    with pytest.raises(api.StateStoreError) as caught:
        fn(*args, **kwargs)
    assert caught.value.code == code
    return caught.value


@pytest.mark.tc030_01
@pytest.mark.parametrize("operation", ["apply", "advance_epoch"])
@pytest.mark.parametrize(
    "field,value",
    [
        ("subject_id", "subject-other"),
        ("family_member_id", "member-other"),
        ("role", "admin"),
        ("home_id", "home-other"),
        ("family_member_id", "member-reader"),
    ],
)
def test_exact_scope_before_metadata_or_lookup(api, store, operation, field, value):
    caller = {**context(), field: value}
    kwargs = {"home_id": "home-example"}
    kwargs.update(
        {"device_id": [], "event": {}, "now_ms": False}
        if operation == "apply"
        else {"epoch": False}
    )
    caught = error(api, "forbidden", getattr(store, operation), caller, **kwargs)
    assert caught.path == ("scope",)
    assert read(store).revision == 0


@pytest.mark.tc030_01
@pytest.mark.parametrize("operation", ["apply", "advance_epoch"])
@pytest.mark.parametrize("caller", [None, {}, {**context(), "private-key": "private-value"}])
def test_invalid_context(api, store, operation, caller):
    kwargs = {"home_id": "home-example"}
    kwargs.update(
        {"device_id": [], "event": {}, "now_ms": False}
        if operation == "apply"
        else {"epoch": False}
    )
    error(api, "invalid_context", getattr(store, operation), caller, **kwargs)
    assert read(store).revision == 0


@pytest.mark.tc030_01
@pytest.mark.parametrize("operation", ["apply", "advance_epoch"])
def test_kid_read_only_and_cross_home(api, store, operation):
    caller = context(member="member-child", role="kid")
    kwargs = {"home_id": "home-example"}
    kwargs.update(
        {"device_id": "device-one", "event": event(), "now_ms": 100}
        if operation == "apply"
        else {"epoch": 2}
    )
    error(api, "forbidden", getattr(store, operation), caller, **kwargs)
    kwargs["home_id"] = "home-other"
    error(api, "forbidden", getattr(store, operation), context(), **kwargs)


@pytest.mark.tc030_01
@pytest.mark.parametrize("bad", [True, False, -1, 1.0, "1", None, [], {}])
def test_exact_integer_time_and_epoch(api, store, bad):
    error(api, "invalid_integer", apply, store, now_ms=bad)
    error(api, "invalid_integer", store.advance_epoch, context(), home_id="home-example", epoch=bad)
    assert read(store).revision == 0


@pytest.mark.tc030_01
@pytest.mark.parametrize("bad", [None, True, {}, "", "private value"])
def test_device_identifier(api, store, bad):
    error(api, "invalid_identifier", apply, store, device_id=bad)


@pytest.mark.tc030_01
def test_unknown_device_does_not_inspect_event_or_pin(api):
    store = api.CurrentStateStore(**configuration())
    result = apply(store, {}, device_id="device-missing")
    assert result == api.StateNotFound("home-example", "device-missing")
    assert read(store).revision == 0
    error(api, "epoch_uninitialized", apply, store)


@pytest.mark.tc030_01
@pytest.mark.parametrize(
    "mutation,code",
    [
        ("not_object", "invalid_event"),
        ("extra", "invalid_event"),
        ("missing", "invalid_event"),
        ("home", "identity_mismatch"),
        ("device", "identity_mismatch"),
        ("intent", "unexpected_intent"),
        ("report_order", "invalid_event"),
        ("availability_order", "invalid_event"),
        ("bad_time", "invalid_event"),
        ("bad_value", "invalid_event"),
        ("future_report", "epoch_mismatch"),
        ("old_availability", "epoch_mismatch"),
    ],
)
def test_rejected_event_zero_publication(api, store, mutation, code):
    data = event()
    if mutation == "not_object":
        data = []
    elif mutation == "extra":
        data["private-key"] = "private-value"
    elif mutation == "missing":
        del data["reported_state"]
    elif mutation in ("home", "device"):
        data[mutation + "_id"] = mutation + "-other"
    elif mutation == "intent":
        data["desired_state"] = {"revision": 1, "values": {"is_on": True}, "report_baseline": None}
    elif mutation == "report_order":
        data["reported_state"]["is_on"] = {
            "status": "unknown",
            "value": None,
            "ordering": None,
            "observed_at": None,
        }
    elif mutation == "availability_order":
        data["availability"] = {"status": "unknown", "ordering": None, "observed_at": None}
    elif mutation == "bad_time":
        data["availability"]["observed_at"] = "2026-02-30T00:00:00Z"
    elif mutation == "bad_value":
        data["reported_state"]["is_on"]["value"] = float("nan")
    elif mutation == "future_report":
        data["reported_state"]["is_on"]["ordering"]["epoch"] = 2
    else:
        data["availability"]["ordering"]["epoch"] = 0
    before = read(store).to_dict()
    original = copy.deepcopy(data)
    caught = error(api, code, apply, store, data)
    assert caught.__context__ is None
    assert caught.path == ("event",)
    assert "private" not in str(caught)
    assert read(store).to_dict() == before
    # NaN does not equal itself; compare the unchanged shape for this case.
    if mutation != "bad_value":
        assert data == original
    assert apply(store).revision == 1


@pytest.mark.tc030_01
def test_inputs_and_results_detached(store):
    data = event()
    result = apply(store, data)
    data["reported_state"].clear()
    projection = result.to_dict()
    projection["state"]["reported_state"].clear()
    assert dict(read(store).state.reported_state)["is_on"].value is False
    with pytest.raises(FrozenInstanceError):
        result.revision = 99


@pytest.mark.tc030_02
def test_newer_same_value_is_observation_and_timestamp_is_not_order(store):
    first = apply(store)
    newer = event(sequence=2)
    newer["availability"]["observed_at"] = "2020-01-01T00:00:00Z"
    newer["reported_state"]["is_on"]["observed_at"] = "2020-01-01T00:00:00Z"
    result = apply(store, newer, now_ms=101)
    assert first.revision == 1 and result.revision == 2 and result.updated_at_ms == 101
    assert dict(result.state.reported_state)["is_on"].observed_at == "2020-01-01T00:00:00Z"


@pytest.mark.tc030_02
@pytest.mark.parametrize("sequence", [0, 1])
def test_stale_and_replay_never_refresh(store, sequence):
    first = apply(store)
    result = apply(store, event(sequence=sequence), now_ms=200)
    assert result.state == first.state
    assert result.revision == 1 and result.updated_at_ms == 100 and result.freshness == "stale"
    assert read(store, now_ms=110, max_age_ms=10).freshness == "fresh"
    assert read(store, now_ms=111, max_age_ms=10).freshness == "stale"


@pytest.mark.tc030_02
@pytest.mark.parametrize("change", ["value", "scalar_type", "timestamp", "availability"])
def test_conflict_rejects_entire_delta(api, store, change):
    apply(store, event(value=0))
    data = event(value=0)
    if change == "value":
        data["reported_state"]["is_on"]["value"] = 1
    elif change == "scalar_type":
        data["reported_state"]["is_on"]["value"] = 0.0
    elif change == "timestamp":
        data["reported_state"]["is_on"]["observed_at"] = "2026-10-17T00:00:01Z"
    else:
        data["availability"]["status"] = "offline"
    # Include a fresh new report before the conflicting member: no partial publication.
    data["reported_state"] = {
        "temperature_c": {**event(sequence=9)["reported_state"]["is_on"], "value": 20},
        **data["reported_state"],
    }
    before = read(store).to_dict()
    error(api, "invalid_event", apply, store, data, now_ms=101)
    assert read(store).to_dict() == before


@pytest.mark.tc030_02
def test_mixed_newer_older_and_new_member_merge(store):
    apply(store, event(sequence=5))
    data = event(sequence=3, value=True)
    data["reported_state"]["temperature_c"] = {
        **event(sequence=3)["reported_state"]["is_on"],
        "value": 0,
    }
    data["reported_state"]["is_on"]["ordering"]["sequence"] = 6
    result = apply(store, data, now_ms=101)
    reports = dict(result.state.reported_state)
    assert result.revision == 2
    assert result.state.availability.ordering.sequence == 5
    assert reports["is_on"].value is True and reports["is_on"].ordering.sequence == 6
    assert reports["temperature_c"].value == 0 and reports["temperature_c"].ordering.sequence == 3


@pytest.mark.tc030_02
@pytest.mark.parametrize("value", [False, 0, 0.0, True, 21.5])
def test_scalar_types_preserved(store, value):
    result = apply(store, event(value=value))
    actual = dict(result.state.reported_state)["is_on"].value
    assert type(actual) is type(value) and actual == value


@pytest.mark.tc030_02
def test_unknown_is_explicit_not_false(store):
    data = event()
    data["reported_state"]["is_on"].update(status="unknown", value=None)
    data["availability"]["status"] = "unknown"
    result = apply(store, data)
    report = dict(result.state.reported_state)["is_on"]
    assert report.status == "unknown" and report.value is None
    assert result.state.availability.status == "unknown"


@pytest.mark.tc030_02
@pytest.mark.parametrize("sequence", [0, 1, 2])
def test_regressing_clock_rejected_even_for_noop(api, store, sequence):
    apply(store)
    error(api, "clock_regression", apply, store, event(sequence=sequence), now_ms=99)
    assert read(store).revision == 1 and read(store).updated_at_ms == 100


@pytest.mark.tc030_02
def test_concurrent_identical_events_publish_once(store):
    barrier = Barrier(12)

    def deliver(_):
        barrier.wait()
        return apply(store).revision

    with ThreadPoolExecutor(max_workers=12) as pool:
        revisions = list(pool.map(deliver, range(12)))
    assert revisions == [1] * 12
    assert read(store).revision == 1


@pytest.mark.tc030_02
def test_concurrent_disjoint_reports_no_lost_updates(store):
    barrier = Barrier(8)

    def deliver(n):
        data = event()
        data["reported_state"] = {"property_" + str(n): data["reported_state"]["is_on"]}
        barrier.wait()
        return apply(store, data).revision

    with ThreadPoolExecutor(max_workers=8) as pool:
        revisions = list(pool.map(deliver, range(8)))
    assert sorted(revisions) == list(range(1, 9))
    assert len(read(store).state.reported_state) == 8


@pytest.mark.tc030_02
def test_put_cas_and_apply_share_publication_lock(api, store):
    barrier = Barrier(2)

    def replace():
        barrier.wait()
        try:
            return store.put(
                context(), **ARGS, state=event(value=True), expected_revision=0, now_ms=100
            ).revision
        except api.StateStoreError as exc:
            return exc.code

    def deliver():
        barrier.wait()
        return apply(store, event(sequence=2)).revision

    with ThreadPoolExecutor(max_workers=2) as pool:
        put_result, apply_result = pool.submit(replace), pool.submit(deliver)
        p, a = put_result.result(), apply_result.result()
    assert (p, a) in [(1, 2), ("revision_conflict", 1)]
    assert dict(read(store).state.reported_state)["is_on"].value is False
    assert read(store).revision == a


@pytest.mark.tc030_03
def test_epoch_pin_is_explicit_and_does_not_refresh_or_allocate(api):
    store = api.CurrentStateStore(**configuration())
    error(api, "epoch_uninitialized", apply, store)
    assert store.advance_epoch(context(), home_id="home-example", epoch=0) == 0
    assert apply(store, event(epoch=0)).revision == 1
    before = read(store).to_dict()
    for epoch in [1, 1, 2]:
        assert store.advance_epoch(context(), home_id="home-example", epoch=epoch) == epoch
        assert read(store).to_dict() == before
    error(api, "epoch_regression", store.advance_epoch, context(), home_id="home-example", epoch=1)
    error(api, "epoch_mismatch", apply, store, event(epoch=1, sequence=99))
    assert apply(store, event(epoch=2, sequence=0), now_ms=101).revision == 2


@pytest.mark.tc030_03
@pytest.mark.parametrize("epoch", [0, 2])
@pytest.mark.parametrize("device", ["device-one", "device-two"])
def test_old_and_future_callbacks_fenced_across_devices(api, store, epoch, device):
    error(api, "epoch_mismatch", apply, store, event(epoch=epoch, device=device), device_id=device)
    assert read(store, device_id=device).revision == 0
    assert apply(store, event(device=device), device_id=device).revision == 1


@pytest.mark.tc030_03
def test_home_independence_and_new_store_reset(api, store):
    store.advance_epoch(context(), home_id="home-example", epoch=5)
    store.advance_epoch(context("home-other"), home_id="home-other", epoch=1)
    data = event()
    data["home_id"] = "home-other"
    other = store.apply(
        context("home-other"), home_id="home-other", device_id="device-one", event=data, now_ms=100
    )
    assert other.revision == 1 and read(store).revision == 0
    restarted = api.CurrentStateStore(**configuration())
    assert read(restarted).revision == 0
    error(api, "epoch_uninitialized", apply, restarted)


@pytest.mark.tc030_03
@pytest.mark.parametrize("source", ["report", "availability", "baseline", "rebuild"])
def test_pin_cannot_lower_snapshot_source_epochs(api, source):
    store = api.CurrentStateStore(**configuration())
    data = event()
    if source == "report":
        data["reported_state"]["is_on"]["ordering"]["epoch"] = 3
    elif source == "availability":
        data["availability"]["ordering"]["epoch"] = 3
    elif source == "baseline":
        data["desired_state"] = {
            "revision": 1,
            "values": {"is_on": True},
            "report_baseline": {"epoch": 3, "sequence": 0},
        }
    else:
        data = event(epoch=3)
    if source == "rebuild":
        store.rebuild(
            context(),
            home_id="home-example",
            now_ms=100,
            states={"schema_version": 1, "states": [data, event(device="device-two")]},
        )
    else:
        store.put(context(), **ARGS, state=data, expected_revision=0, now_ms=100)
    before = read(store).to_dict()
    error(api, "epoch_regression", store.advance_epoch, context(), home_id="home-example", epoch=2)
    assert read(store).to_dict() == before
    assert store.advance_epoch(context(), home_id="home-example", epoch=3) == 3
    assert apply(store, event(epoch=3, sequence=2), now_ms=101).revision == 2


@pytest.mark.tc030_03
def test_put_after_pin_requires_new_pin_and_failed_event_does_not_repin(api, store):
    store.put(context(), **ARGS, state=event(epoch=3), expected_revision=0, now_ms=100)
    error(api, "invalid_event", apply, store, event(sequence=2), now_ms=101)
    error(api, "epoch_mismatch", apply, store, event(epoch=3, sequence=2), now_ms=101)
    store.advance_epoch(context(), home_id="home-example", epoch=3)
    assert apply(store, event(epoch=3, sequence=2), now_ms=101).revision == 2


@pytest.mark.tc030_03
def test_apply_blocks_one_shot_rebuild(api, store):
    apply(store)
    error(
        api,
        "already_initialized",
        store.rebuild,
        context(),
        home_id="home-example",
        now_ms=101,
        states={"schema_version": 1, "states": [event(), event(device="device-two")]},
    )
    assert read(store).revision == 1


@pytest.mark.tc030_03
def test_empty_home_pin_is_monotonic(api):
    config = configuration()
    config["inventories"][0]["devices"].clear()
    store = api.CurrentStateStore(**config)
    store.advance_epoch(context(), home_id="home-example", epoch=2)
    error(api, "epoch_regression", store.advance_epoch, context(), home_id="home-example", epoch=1)
    assert isinstance(apply(store), api.StateNotFound)


@pytest.mark.tc030_03
def test_concurrent_pins_never_regress(api, store):
    barrier = Barrier(8)

    def pin(epoch):
        barrier.wait()
        try:
            return store.advance_epoch(context(), home_id="home-example", epoch=epoch)
        except api.StateStoreError as exc:
            assert exc.code == "epoch_regression"
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(pin, range(2, 10)))
    assert store.advance_epoch(context(), home_id="home-example", epoch=9) == 9
    error(api, "epoch_mismatch", apply, store, event(epoch=8))
    assert apply(store, event(epoch=9)).revision == 1


@pytest.mark.tc030_03
def test_advance_and_old_callback_are_atomic(api, store):
    barrier = Barrier(2)

    def pin():
        barrier.wait()
        return store.advance_epoch(context(), home_id="home-example", epoch=2)

    def deliver():
        barrier.wait()
        try:
            return apply(store).revision
        except api.StateStoreError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        advanced, delivered = pool.submit(pin), pool.submit(deliver)
        assert advanced.result() == 2
        outcome = delivered.result()
    assert outcome in (1, "epoch_mismatch")
    before = read(store).to_dict()
    error(api, "epoch_mismatch", apply, store, event(sequence=99), now_ms=101)
    assert read(store).to_dict() == before


@pytest.mark.tc030_03
def test_offline_recovery_preserves_intent_reports_and_convergence(store):
    from state_schema.canonical_state import evaluate_convergence

    data = event()
    data["desired_state"] = {
        "revision": 4,
        "values": {"is_on": True},
        "report_baseline": {"epoch": 1, "sequence": 1},
    }
    data["reported_state"]["temperature_c"] = {
        **data["reported_state"]["is_on"],
        "value": 0,
    }
    store.put(context(), **ARGS, state=data, expected_revision=0, now_ms=100)
    offline = apply(store, event(sequence=2, status="offline"), now_ms=101)
    assert offline.state.desired_state.to_dict() == data["desired_state"]
    assert offline.state.to_dict()["reported_state"] == data["reported_state"]
    assert evaluate_convergence(offline.state.to_dict(), current_epoch=1) == "unknown"
    recovery = apply(store, event(sequence=3, value=True), now_ms=102)
    assert recovery.revision == 3 and recovery.state.desired_state == offline.state.desired_state
    assert dict(recovery.state.reported_state)["temperature_c"].value == 0
    assert evaluate_convergence(recovery.state.to_dict(), current_epoch=1) == "confirmed"


@pytest.mark.tc030_03
def test_real_normalizer_to_store_offline_and_recovery(store):
    # Reuse accepted adapter's fictional configuration, not a replacement adapter.
    from ha_normalization_artifact_smoke import event as frame
    from ha_normalization_artifact_smoke import fixture as normalizer_configuration
    from home_device_fabric.ha_normalization import HAEventNormalizer

    normalizer = HAEventNormalizer(**normalizer_configuration())
    # Adapter fixture identity is canonical device-example, so build matching registry/grants.
    from state_store_artifact_smoke import inventory

    config = configuration()
    config["inventories"][0] = inventory()
    config["inventories"][0]["devices"][0]["id"] = "device-example"
    api = importlib.import_module("home_device_fabric.state_store")
    integrated = api.CurrentStateStore(**config)
    integrated.advance_epoch(context(), home_id="home-example", epoch=1)
    for seq, value, status in [
        (1, "on", "online"),
        (2, "unavailable", "offline"),
        (3, "off", "online"),
    ]:
        delta = normalizer.normalize(frame(value), ordering={"epoch": 1, "sequence": seq})
        result = integrated.apply(
            context(),
            home_id="home-example",
            device_id="device-example",
            event=delta.to_dict(),
            now_ms=100 + seq,
        )
        assert result.revision == seq and result.state.availability.status == status
        assert dict(result.state.reported_state)["is_on"].value is (seq != 3)


@pytest.mark.tc030_04
def test_installed_smoke_contract_offline(offline):
    assert check() == {"checks": 18, "offline": True}
    assert offline == []
