"""REQ-030 literal state-store event integration and atomicity probes."""

import copy
import importlib
import pickle
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from threading import Barrier

import pytest
from ha_normalization_artifact_smoke import event as ha_event
from ha_normalization_artifact_smoke import fixture as ha_fixture
from state_events_artifact_smoke import check
from state_store_artifact_smoke import configuration, context, snapshot

ARGS = {"home_id": "home-example", "device_id": "device-one"}


@pytest.fixture
def api():
    return importlib.import_module("home_device_fabric.state_store")


@pytest.fixture
def store(api):
    result = api.CurrentStateStore(**configuration())
    result.advance_epoch(context(), home_id="home-example", epoch=1)
    return result


def delta(sequence=1, epoch=1, value=False, member="is_on", availability="online"):
    result = snapshot(value=value)
    report = result["reported_state"].pop("is_on")
    report["ordering"] = {"epoch": epoch, "sequence": sequence}
    if member is not None:
        result["reported_state"][member] = report
    result["availability"]["status"] = availability
    result["availability"]["ordering"] = {"epoch": epoch, "sequence": sequence}
    return result


def apply(store, payload=None, caller=None, **kwargs):
    return store.apply(
        context() if caller is None else caller,
        **{**ARGS, "event": delta() if payload is None else payload, "now_ms": 100, **kwargs},
    )


def read(store, **kwargs):
    return store.read(context(), **{**ARGS, "now_ms": 100, "max_age_ms": 0, **kwargs})


def pin(store, epoch=1, caller=None, **kwargs):
    return store.advance_epoch(
        context() if caller is None else caller,
        **{"home_id": "home-example", "epoch": epoch, **kwargs},
    )


def fails(api, code, fn):
    with pytest.raises(api.StateStoreError) as caught:
        fn()
    assert caught.value.code == code
    return caught.value


@pytest.mark.tc030_01
@pytest.mark.parametrize("operation", ["apply", "pin"])
@pytest.mark.parametrize(
    "change",
    [
        {"subject_id": "other-subject"},
        {"family_member_id": "other-member"},
        {"role": "admin"},
        {"home_id": "home-other"},
        {"family_member_id": "member-reader"},
        {"family_member_id": "member-child", "role": "kid"},
    ],
)
def test_exact_scope_before_all_other_inputs(api, store, operation, change):
    caller = {**context(), **change}
    fn = (
        (lambda: apply(store, {}, caller, device_id=[], now_ms=False))
        if operation == "apply"
        else (lambda: pin(store, False, caller))
    )
    err = fails(api, "forbidden", fn)
    assert err.path == ("scope",)
    assert read(store).revision == 0
    assert pin(store) == 1


@pytest.mark.tc030_01
@pytest.mark.parametrize("operation", ["apply", "pin"])
@pytest.mark.parametrize(
    "caller", [{}, {**context(), "private-key": "private-value"}, {**context(), "role": False}]
)
def test_invalid_context(api, store, operation, caller):
    def fn():
        return apply(store, {}, caller) if operation == "apply" else pin(store, 2, caller)

    assert fails(api, "invalid_context", fn).path == ("context",)
    assert read(store).revision == 0


@pytest.mark.tc030_01
@pytest.mark.parametrize("operation", ["apply", "pin"])
@pytest.mark.parametrize("home", ["home-other", "home-secret", [], None])
def test_cross_home_denial_precedes_metadata(api, store, operation, home):
    def fn():
        return (
            apply(store, {}, home_id=home, now_ms=False)
            if operation == "apply"
            else pin(store, False, home_id=home)
        )

    assert fails(api, "forbidden", fn).path == ("scope",)
    assert read(store).revision == 0


@pytest.mark.tc030_01
@pytest.mark.parametrize("field", ["now_ms", "epoch"])
@pytest.mark.parametrize("bad", [True, None, -1, 1.0, "1"])
def test_exact_integer_metadata(api, store, field, bad):
    fn = (lambda: apply(store, now_ms=bad)) if field == "now_ms" else lambda: pin(store, bad)
    assert fails(api, "invalid_integer", fn).path == (field,)
    assert read(store).revision == 0


@pytest.mark.tc030_01
@pytest.mark.parametrize("device", [None, [], True, "PRIVATE.id", ""])
def test_invalid_identifier(api, store, device):
    fails(api, "invalid_identifier", lambda: apply(store, device_id=device))
    assert read(store).revision == 0


@pytest.mark.tc030_01
def test_unknown_device_does_not_parse_event_or_register(api, store):
    result = apply(store, {}, device_id="device-missing")
    assert type(result) is api.StateNotFound
    assert type(read(store, device_id="device-missing")) is api.StateNotFound
    assert read(store).revision == 0


@pytest.mark.tc030_01
@pytest.mark.parametrize(
    "mutation,code",
    [
        ("extra", "invalid_event"),
        ("shape", "invalid_event"),
        ("home", "identity_mismatch"),
        ("device", "identity_mismatch"),
        ("desired", "unexpected_intent"),
        ("report_order", "invalid_event"),
        ("availability_order", "invalid_event"),
        ("report_epoch", "epoch_mismatch"),
        ("availability_epoch", "epoch_mismatch"),
        ("bad_value", "invalid_event"),
    ],
)
def test_failed_event_is_atomic_and_detached(api, store, mutation, code):
    apply(store)
    candidate = delta(2)
    if mutation == "extra":
        candidate["private-key"] = "private-value"
    elif mutation == "shape":
        candidate = {}
    elif mutation == "home":
        candidate["home_id"] = "home-other"
    elif mutation == "device":
        candidate["device_id"] = "device-two"
    elif mutation == "desired":
        candidate["desired_state"] = {
            "revision": 1,
            "values": {"is_on": True},
            "report_baseline": None,
        }
    elif mutation == "report_order":
        candidate["reported_state"]["is_on"]["ordering"] = None
        candidate["reported_state"]["is_on"]["observed_at"] = None
        candidate["reported_state"]["is_on"]["status"] = "unknown"
        candidate["reported_state"]["is_on"]["value"] = None
    elif mutation == "availability_order":
        candidate["availability"] = {"status": "unknown", "ordering": None, "observed_at": None}
    elif mutation == "report_epoch":
        candidate["reported_state"]["is_on"]["ordering"]["epoch"] = 2
    elif mutation == "availability_epoch":
        candidate["availability"]["ordering"]["epoch"] = 0
    else:
        candidate["reported_state"]["is_on"]["value"] = []
    original = copy.deepcopy(candidate)
    before = read(store).to_dict()
    err = fails(api, code, lambda: apply(store, candidate))
    assert err.path == ("event",)
    assert read(store).to_dict() == before and candidate == original


@pytest.mark.tc030_02
@pytest.mark.parametrize("value", [False, 0, 0.0, "unchanged"])
def test_new_observation_same_value_bumps_once_then_replay_and_stale_do_not(store, value):
    first = apply(store, delta(2, value=value))
    assert first.revision == 1 and first.updated_at_ms == 100
    saved = apply(store, delta(3, value=value), now_ms=110)
    assert saved.revision == 2 and saved.updated_at_ms == 110
    for payload in (delta(3, value=value), delta(2, value=True)):
        ignored = apply(store, payload, now_ms=120)
        assert ignored.revision == 2 and ignored.updated_at_ms == 110
        assert ignored.freshness == "stale"
        assert ignored.state.to_dict() == saved.state.to_dict()
    assert read(store, now_ms=120, max_age_ms=9).freshness == "stale"
    assert read(store, now_ms=120, max_age_ms=10).freshness == "fresh"


@pytest.mark.tc030_02
@pytest.mark.parametrize("conflict", ["value", "type", "time", "availability"])
def test_conflicting_replay_rejects_entire_event(api, store, conflict):
    apply(store, delta(2, value=0))
    before = read(store).to_dict()
    payload = delta(2, value=0)
    payload["reported_state"]["extra"] = delta(3)["reported_state"]["is_on"]
    if conflict == "value":
        payload["reported_state"]["is_on"]["value"] = 1
    elif conflict == "type":
        payload["reported_state"]["is_on"]["value"] = 0.0
    elif conflict == "time":
        payload["reported_state"]["is_on"]["observed_at"] = "2026-10-18T00:00:00Z"
    else:
        payload["availability"]["status"] = "offline"
    fails(api, "invalid_event", lambda: apply(store, payload))
    assert read(store).to_dict() == before


@pytest.mark.tc030_02
def test_independent_members_and_desired_preserved(store):
    initial = snapshot()
    initial["desired_state"] = {
        "revision": 7,
        "values": {"is_on": True},
        "report_baseline": {"epoch": 1, "sequence": 1},
    }
    store.put(context(), **ARGS, state=initial, expected_revision=0, now_ms=100)
    apply(store, delta(5, value=True))
    mixed = delta(3, value=False)
    mixed["reported_state"]["temperature_c"] = delta(6, value=22)["reported_state"]["is_on"]
    mixed["availability"]["ordering"]["sequence"] = 7
    view = apply(store, mixed).state.to_dict()
    assert view["desired_state"] == initial["desired_state"]
    assert view["reported_state"]["is_on"]["value"] is True
    assert view["reported_state"]["temperature_c"]["value"] == 22
    assert view["availability"]["ordering"]["sequence"] == 7
    late = apply(store, delta(2, value=0, member="new_member"))
    assert late.revision == 4
    assert late.state.to_dict()["reported_state"]["new_member"]["value"] == 0
    for member, report in view["reported_state"].items():
        assert late.state.to_dict()["reported_state"][member] == report
    assert late.state.to_dict()["availability"] == view["availability"]
    assert late.state.to_dict()["desired_state"] == initial["desired_state"]
    assert read(store, device_id="device-two").revision == 0


@pytest.mark.tc030_02
def test_source_timestamps_never_override_order(store):
    apply(store, delta(2, value=True))
    stale = delta(1)
    stale["availability"]["observed_at"] = "2099-01-01T00:00:00Z"
    stale["reported_state"]["is_on"]["observed_at"] = "2099-01-01T00:00:00Z"
    assert apply(store, stale).revision == 1
    newer = delta(3)
    newer["availability"]["observed_at"] = "2000-01-01T00:00:00Z"
    newer["reported_state"]["is_on"]["observed_at"] = "2000-01-01T00:00:00Z"
    assert apply(store, newer).revision == 2
    assert read(store).state.to_dict()["reported_state"]["is_on"]["value"] is False


def race(functions):
    barrier = Barrier(len(functions), timeout=5)

    def call(fn):
        barrier.wait()
        return fn()

    with ThreadPoolExecutor(max_workers=len(functions)) as pool:
        futures = [pool.submit(call, fn) for fn in functions]
        return [future.result(timeout=10) for future in futures]


@pytest.mark.tc030_02
@pytest.mark.parametrize("mode", ["duplicate", "ordered", "disjoint", "conflicting"])
def test_concurrent_events_no_lost_updates(api, store, mode):
    def submit(index):
        payload = delta(
            1 if mode != "ordered" else index + 1,
            value=index if mode in ("disjoint", "conflicting") else False,
            member=f"member_{index}" if mode == "disjoint" else "is_on",
        )
        try:
            return apply(store, payload)
        except api.StateStoreError as err:
            return err.code

    results = race([lambda i=i: submit(i) for i in range(8)])
    final = read(store)
    if mode == "duplicate":
        assert all(r.revision == 1 for r in results) and final.revision == 1
    elif mode == "ordered":
        assert final.state.to_dict()["reported_state"]["is_on"]["ordering"]["sequence"] == 8
        assert 1 <= final.revision <= 8
    elif mode == "disjoint":
        assert len(final.state.reported_state) == 8 and final.revision == 8
        assert all(
            final.state.to_dict()["reported_state"][f"member_{i}"]["value"] == i for i in range(8)
        )
    else:
        assert results.count("invalid_event") == 7 and final.revision == 1


@pytest.mark.tc030_02
@pytest.mark.parametrize("operation", ["put", "rebuild"])
def test_event_and_snapshot_share_publication_lock(api, store, operation):
    def replace():
        try:
            if operation == "put":
                return store.put(context(), **ARGS, state=delta(1), expected_revision=0, now_ms=100)
            return store.rebuild(
                context(),
                home_id="home-example",
                now_ms=100,
                states={"schema_version": 1, "states": [delta(1), snapshot(device="device-two")]},
            )
        except api.StateStoreError as err:
            return err.code

    result, _ = race([replace, lambda: apply(store, delta(2, value=True))])
    assert read(store).state.to_dict()["reported_state"]["is_on"]["value"] is True
    assert read(store).revision == (1 if type(result) is str else 2)
    assert read(store, device_id="device-two").revision == (
        1 if operation == "rebuild" and type(result) is not str else 0
    )


@pytest.mark.tc030_03
def test_epochs_unset_monotonic_and_home_isolation(api):
    store = api.CurrentStateStore(**configuration())
    fails(api, "epoch_uninitialized", lambda: apply(store, {}))
    assert pin(store, 0) == 0
    assert pin(store, 1) == 1
    first = apply(store)
    assert pin(store, 1) == 1 and pin(store, 2) == 2
    assert read(store).to_dict() == first.to_dict()
    fails(api, "epoch_regression", lambda: pin(store, 1))
    for epoch in (0, 1, 3):
        fails(api, "epoch_mismatch", lambda: apply(store, delta(999, epoch=epoch)))
    assert apply(store, delta(0, epoch=2, value=True)).revision == 2
    assert pin(store, 0, context("home-other"), home_id="home-other") == 0
    other = delta(0, epoch=0)
    other["home_id"] = "home-other"
    assert apply(store, other, context("home-other"), home_id="home-other").revision == 1
    assert read(store).revision == 2
    assert pin(api.CurrentStateStore(**configuration()), 0) == 0


@pytest.mark.tc030_03
@pytest.mark.parametrize("source", ["report", "availability", "desired"])
@pytest.mark.parametrize("initialize", ["put", "rebuild"])
def test_pin_cannot_lower_any_stored_generation(api, store, source, initialize):
    state = snapshot(device="device-two")
    if source == "report":
        state["reported_state"]["is_on"]["ordering"]["epoch"] = 4
    elif source == "availability":
        state["availability"]["ordering"]["epoch"] = 4
    else:
        state["desired_state"] = {
            "revision": 1,
            "values": {"is_on": True},
            "report_baseline": {"epoch": 4, "sequence": 0},
        }
    if initialize == "rebuild" and source == "desired":
        # Rebuild deliberately forbids desired intent (accepted REQ-029).
        fails(
            api,
            "unexpected_intent",
            lambda: store.rebuild(
                context(),
                home_id="home-example",
                now_ms=100,
                states={"schema_version": 1, "states": [snapshot(), state]},
            ),
        )
        return
    if initialize == "put":
        store.put(
            context(),
            home_id="home-example",
            device_id="device-two",
            state=state,
            expected_revision=0,
            now_ms=100,
        )
    else:
        store.rebuild(
            context(),
            home_id="home-example",
            now_ms=100,
            states={"schema_version": 1, "states": [snapshot(), state]},
        )
    fails(api, "epoch_regression", lambda: pin(store, 3))
    # Rejected advance must not change the prior pin.
    assert apply(store, delta(2)).revision == (2 if initialize == "rebuild" else 1)
    assert pin(store, 4) == 4
    fails(api, "epoch_mismatch", lambda: apply(store, delta(3)))


@pytest.mark.tc030_03
def test_pin_and_event_race_fences_old_callback(api, store):
    def old_callback():
        try:
            return apply(store).revision
        except api.StateStoreError as err:
            return err.code

    result, generation = race([old_callback, lambda: pin(store, 2)])
    assert generation == 2 and result in (1, "epoch_mismatch")
    assert apply(store, delta(0, epoch=2, value=True)).revision == (2 if result == 1 else 1)
    fails(api, "epoch_mismatch", lambda: apply(store, delta(100)))


@pytest.mark.tc030_03
def test_real_normalizer_offline_unknown_recovery(api):
    from home_device_fabric.ha_normalization import HAEventNormalizer

    config = ha_fixture()
    store = api.CurrentStateStore(
        inventories=[config["inventory"]], grants=[{**context(), "access": "write"}]
    )
    pin(store)
    normalizer = HAEventNormalizer(**config)
    last_known = None
    for seq, raw in enumerate(("on", "unavailable", None, "off", "unknown", "on"), 1):
        event = ha_event("off" if raw is None else raw)
        if raw is None:
            event["data"]["new_state"] = None
        payload = normalizer.normalize(event, ordering={"epoch": 1, "sequence": seq}).to_dict()
        view = apply(store, payload, device_id="device-example")
        state = view.state.to_dict()
        assert view.revision == seq
        if raw in ("unavailable", None):
            assert state["availability"]["status"] == "offline"
            assert state["reported_state"] == last_known
        elif raw == "unknown":
            assert state["reported_state"]["is_on"]["status"] == "unknown"
            assert state["reported_state"]["is_on"]["value"] is None
        else:
            assert state["availability"]["status"] == "online"
            assert state["reported_state"]["is_on"]["value"] is (raw == "on")
            last_known = state["reported_state"]


@pytest.mark.tc030_01
@pytest.mark.tc030_03
def test_clock_priority_even_for_noop_or_malformed_event(api, store):
    apply(store)
    before = read(store).to_dict()
    for payload in ({}, delta(), delta(0)):
        fails(api, "clock_regression", lambda: apply(store, payload, now_ms=99))
    assert read(store).to_dict() == before


@pytest.mark.tc030_04
def test_private_errors_detachment_immutability_and_serialization(api, store):
    payload = delta()
    view = apply(store, payload)
    payload["reported_state"].clear()
    projection = view.to_dict()
    projection["state"]["reported_state"].clear()
    assert len(read(store).state.reported_state) == 1
    with pytest.raises(FrozenInstanceError):
        view.revision = 9
    for clone in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(TypeError, match="state_store_serialization_forbidden"):
            clone(store)
    assert repr(store) == "CurrentStateStore()"
    malformed = delta(2)
    malformed["reported_state"]["private-key"] = {
        "status": "known",
        "value": {"private-data": "private-value"},
        "ordering": {"epoch": 1, "sequence": 2},
        "observed_at": "2026-10-18T00:00:00Z",
    }
    err = fails(api, "invalid_event", lambda: apply(store, malformed))
    assert str(err) == "invalid_event: event" and err.__cause__ is None
    assert err.__suppress_context__
    assert "private-" not in "".join(traceback.format_exception(err))
    assert read(store).revision == 1


@pytest.mark.tc030_04
def test_file_environment_denial(api, monkeypatch):
    import builtins
    import os

    def deny(*args, **kwargs):
        pytest.fail("ambient file I/O attempted")

    monkeypatch.setattr(builtins, "open", deny)
    monkeypatch.setattr(os, "environ", {})
    store = api.CurrentStateStore(**configuration())
    pin(store)
    assert apply(store).revision == 1
    assert apply(store).revision == 1
    assert pin(store, 2) == 2


@pytest.mark.tc030_04
def test_installed_integration_checks():
    assert check() == {"checks": 18, "offline": True}
