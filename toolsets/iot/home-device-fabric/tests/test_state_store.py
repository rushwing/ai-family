"""REQ-029 literal scoped snapshot ownership and restart probes."""

import copy
import importlib
import pickle
from dataclasses import FrozenInstanceError

import pytest
from state_store_artifact_smoke import check, configuration, context, inventory, snapshot

ARGS = {"home_id": "home-example", "device_id": "device-one"}


@pytest.fixture
def api():
    return importlib.import_module("home_device_fabric.state_store")


@pytest.fixture
def store(api):
    return api.CurrentStateStore(**configuration())


def read(store, caller=None, **kwargs):
    return store.read(
        context() if caller is None else caller,
        **{
            **ARGS,
            "now_ms": 100,
            "max_age_ms": 10,
            **kwargs,
        },
    )


def put(store, caller=None, **kwargs):
    return store.put(
        context() if caller is None else caller,
        **{
            **ARGS,
            "state": snapshot(),
            "expected_revision": 0,
            "now_ms": 100,
            **kwargs,
        },
    )


def rebuild(store, caller=None, **kwargs):
    return store.rebuild(
        context() if caller is None else caller,
        **{
            "home_id": "home-example",
            "now_ms": 100,
            "states": {"schema_version": 1, "states": [snapshot(), snapshot(device="device-two")]},
            **kwargs,
        },
    )


def error(api, code, function, *args, **kwargs):
    with pytest.raises(api.StateStoreError) as caught:
        function(*args, **kwargs)
    assert caught.value.code == code
    return caught.value


@pytest.mark.tc029_01
@pytest.mark.parametrize(
    "mutation",
    [
        "inventories_object",
        "grants_object",
        "bad_inventory",
        "duplicate_home",
        "bad_grant",
        "grant_extra",
        "grant_missing",
        "unknown_home",
        "duplicate_grant",
        "bad_access",
        "kid_write",
        "bad_subject",
        "bad_role",
        "bad_home",
    ],
)
def test_configuration_rejects_without_mutation(api, mutation):
    config = configuration()
    if mutation == "inventories_object":
        config["inventories"] = {}
    elif mutation == "grants_object":
        config["grants"] = {}
    elif mutation == "bad_inventory":
        config["inventories"][0]["private-key"] = "private-value"
    elif mutation == "duplicate_home":
        config["inventories"].append(inventory())
    elif mutation == "bad_grant":
        config["grants"][0] = None
    elif mutation == "grant_extra":
        config["grants"][0]["private-key"] = "private-value"
    elif mutation == "grant_missing":
        del config["grants"][0]["role"]
    elif mutation == "unknown_home":
        config["grants"][0]["home_id"] = "home-missing"
    elif mutation == "duplicate_grant":
        config["grants"].append(copy.deepcopy(config["grants"][0]))
    elif mutation == "bad_access":
        config["grants"][0]["access"] = True
    elif mutation == "kid_write":
        config["grants"][0]["role"] = "kid"
    elif mutation == "bad_subject":
        config["grants"][0]["subject_id"] = ""
    elif mutation == "bad_role":
        config["grants"][0]["role"] = "owner"
    else:
        config["grants"][0]["home_id"] = False
    before = copy.deepcopy(config)
    caught = error(api, "invalid_configuration", api.CurrentStateStore, **config)
    assert config == before
    assert "private" not in str(caught)


@pytest.mark.tc029_01
def test_configuration_detached_and_empty_fail_closed(api):
    config = configuration()
    store = api.CurrentStateStore(**config)
    config["inventories"][0]["devices"].clear()
    config["grants"][0]["access"] = "read"
    assert put(store).revision == 1
    assert read(store).revision == 1
    empty = api.CurrentStateStore(inventories=[], grants=[])
    assert str(error(api, "forbidden", read, empty)) == "forbidden: scope"
    no_grants = api.CurrentStateStore(inventories=[inventory()], grants=[])
    error(api, "forbidden", read, no_grants)


@pytest.mark.tc029_01
@pytest.mark.parametrize("operation", ["read", "put", "rebuild"])
@pytest.mark.parametrize(
    "changed,value",
    [
        ("subject_id", "subject-other"),
        ("family_member_id", "member-other"),
        ("role", "admin"),
        ("home_id", "home-other"),
    ],
)
def test_each_scope_component_enforced(api, store, operation, changed, value):
    caller = {**context(), changed: value}
    caught = error(
        api, "forbidden", {"read": read, "put": put, "rebuild": rebuild}[operation], store, caller
    )
    assert caught.path == ("scope",)
    assert read(store).revision == 0


@pytest.mark.tc029_01
@pytest.mark.parametrize("operation", ["read", "put", "rebuild"])
@pytest.mark.parametrize(
    "caller",
    [
        None,
        {},
        {**context(), "private-key": "private-value"},
        {**context(), "family_member_id": False},
    ],
)
def test_invalid_context_never_escapes_or_mutates(api, store, operation, caller):
    method = getattr(store, operation)
    kwargs = {"home_id": "home-example", "now_ms": 100}
    if operation == "read":
        kwargs.update(device_id="device-one", max_age_ms=0)
    elif operation == "put":
        kwargs.update(device_id="device-one", expected_revision=0, state={})
    else:
        kwargs.update(states={})
    caught = error(api, "invalid_context", method, caller, **kwargs)
    assert str(caught) == "invalid_context: context"
    assert read(store).revision == 0


@pytest.mark.tc029_01
@pytest.mark.parametrize(
    "caller", [context(member="member-reader"), context(member="member-child", role="kid")]
)
def test_read_grants_and_children_cannot_mutate(api, store, caller):
    assert read(store, caller).revision == 0
    error(api, "forbidden", put, store, caller)
    error(api, "forbidden", rebuild, store, caller)
    assert read(store).revision == 0


@pytest.mark.tc029_01
@pytest.mark.parametrize("operation", ["read", "put", "rebuild"])
@pytest.mark.parametrize("home", ["home-other", "home-secret", [], None])
def test_denied_home_precedes_lookup_and_bad_payload(api, store, operation, home):
    kwargs = {"home_id": home, "now_ms": False}
    if operation == "read":
        kwargs.update(device_id=[], max_age_ms=False)
    elif operation == "put":
        kwargs.update(device_id=[], state={}, expected_revision=False)
    else:
        kwargs.update(states={})
    caught = error(api, "forbidden", getattr(store, operation), context(), **kwargs)
    assert str(caught) == "forbidden: scope"
    assert read(store).revision == 0


@pytest.mark.tc029_02
def test_initial_unknown_and_detached_snapshot(store):
    view = read(store)
    assert view.to_dict() == {
        "status": "found",
        "revision": 0,
        "updated_at_ms": None,
        "freshness": "uninitialized",
        "state": {
            "home_id": "home-example",
            "device_id": "device-one",
            "desired_state": None,
            "reported_state": {},
            "availability": {"status": "unknown", "observed_at": None, "ordering": None},
        },
    }
    candidate = snapshot()
    saved = put(store, state=candidate)
    candidate["reported_state"]["is_on"]["value"] = True
    projection = saved.to_dict()
    projection["state"]["reported_state"].clear()
    assert read(store).state.to_dict() == snapshot()
    with pytest.raises(FrozenInstanceError):
        saved.revision = 9
    with pytest.raises(FrozenInstanceError):
        saved.state.home_id = "home-other"
    assert view.revision == 0 and not view.state.reported_state


@pytest.mark.tc029_02
@pytest.mark.parametrize("operation", ["read", "put"])
def test_unknown_device_typed_and_never_created(api, store, operation):
    result = {"read": read, "put": put}[operation](store, device_id="missing-device")
    assert type(result) is api.StateNotFound
    assert result.to_dict() == {
        "status": "not_found",
        "home_id": "home-example",
        "device_id": "missing-device",
    }
    assert type(read(store, device_id="missing-device")) is api.StateNotFound
    assert read(store).revision == 0


@pytest.mark.tc029_02
@pytest.mark.parametrize("bad", [None, True, "", "PRIVATE.device", [], 1])
@pytest.mark.parametrize("operation", ["read", "put"])
def test_invalid_device(api, store, operation, bad):
    caught = error(
        api, "invalid_identifier", {"read": read, "put": put}[operation], store, device_id=bad
    )
    assert caught.path == ("device_id",)


@pytest.mark.tc029_02
@pytest.mark.parametrize(
    "state,code",
    [
        ({}, "invalid_state"),
        ({**snapshot(), "private-key": "private-value"}, "invalid_state"),
        ({**snapshot(), "home_id": "home-other"}, "identity_mismatch"),
        ({**snapshot(), "device_id": "device-two"}, "identity_mismatch"),
        ({**snapshot(), "availability": {}}, "invalid_state"),
    ],
)
def test_invalid_put_atomic_and_private(api, store, state, code):
    before = read(store).to_dict()
    caught = error(api, code, put, store, state=state)
    assert "private" not in str(caught)
    assert read(store).to_dict() == before


@pytest.mark.tc029_02
def test_per_device_and_home_cas_revisions(api, store):
    assert put(store).revision == 1
    error(api, "revision_conflict", put, store)
    assert put(store, expected_revision=1).revision == 2
    assert read(store).revision == 2
    assert read(store, device_id="device-two").revision == 0
    other = read(store, context("home-other"), home_id="home-other")
    assert other.revision == 0 and not other.state.reported_state
    assert (
        put(
            store, context("home-other"), home_id="home-other", state=snapshot("home-other")
        ).revision
        == 1
    )
    assert read(store).revision == 2


@pytest.mark.tc029_02
@pytest.mark.parametrize("value", [False, 0, 0.0, "unknown-text"])
def test_full_snapshot_preserves_typed_values_and_desired(store, value):
    candidate = snapshot(value=value)
    candidate["desired_state"] = {
        "revision": 1,
        "values": {"is_on": True},
        "report_baseline": {"epoch": 1, "sequence": 0},
    }
    result = put(store, state=candidate).state.to_dict()
    assert result == candidate
    assert type(result["reported_state"]["is_on"]["value"]) is type(value)
    assert result["desired_state"] == candidate["desired_state"]


@pytest.mark.tc029_02
@pytest.mark.tc029_03
@pytest.mark.parametrize("operation", ["put", "rebuild"])
def test_concurrent_writers_have_exactly_one_winner(api, store, operation):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    barrier = Barrier(2, timeout=3)

    def race():
        barrier.wait()
        try:
            result = {"put": put, "rebuild": rebuild}[operation](store)
            return "ok", result
        except api.StateStoreError as caught:
            return caught.code, None

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(race) for _ in range(2)]
        results = [future.result(timeout=5) for future in futures]
    assert sorted(code for code, _ in results) == sorted(
        ["ok", "revision_conflict" if operation == "put" else "already_initialized"]
    )
    assert read(store).revision == 1
    assert read(store, device_id="device-two").revision == (1 if operation == "rebuild" else 0)


@pytest.mark.tc029_03
@pytest.mark.parametrize(
    "elapsed,age,expected", [(0, 0, "fresh"), (10, 10, "fresh"), (11, 10, "stale"), (1, 0, "stale")]
)
def test_explicit_freshness_boundaries(store, elapsed, age, expected):
    put(store)
    before = read(store).state.to_dict()
    result = read(store, now_ms=100 + elapsed, max_age_ms=age)
    assert result.freshness == expected
    assert result.revision == 1 and result.updated_at_ms == 100
    assert result.state.to_dict() == before
    assert read(store).state.availability.status == "online"


@pytest.mark.tc029_03
@pytest.mark.parametrize("operation", ["read", "put"])
def test_regressing_elapsed_time_fails_without_change(api, store, operation):
    put(store)
    before = read(store).to_dict()
    kwargs = {"now_ms": 99}
    if operation == "put":
        kwargs["expected_revision"] = 1
    error(api, "clock_regression", {"read": read, "put": put}[operation], store, **kwargs)
    assert read(store).to_dict() == before


@pytest.mark.tc029_03
@pytest.mark.parametrize(
    "operation,field",
    [
        ("read", "now_ms"),
        ("read", "max_age_ms"),
        ("put", "now_ms"),
        ("put", "expected_revision"),
        ("rebuild", "now_ms"),
    ],
)
@pytest.mark.parametrize("value", [None, True, -1, 1.0, "1"])
def test_exact_integer_metadata(api, store, operation, field, value):
    caught = error(
        api,
        "invalid_integer",
        {"read": read, "put": put, "rebuild": rebuild}[operation],
        store,
        **{field: value},
    )
    assert caught.path == (field,)
    assert read(store).revision == 0


@pytest.mark.tc029_03
@pytest.mark.parametrize(
    "mutation,code",
    [
        ("missing", "incomplete_snapshot"),
        ("duplicate", "invalid_state"),
        ("cross_home", "invalid_state"),
        ("unknown", "invalid_state"),
        ("bad_last", "invalid_state"),
        ("desired", "unexpected_intent"),
        ("extra", "invalid_state"),
    ],
)
def test_rebuild_failure_atomic_all_devices(api, store, mutation, code):
    states = [snapshot(), snapshot(device="device-two")]
    if mutation == "missing":
        states.pop()
    elif mutation == "duplicate":
        states[1] = snapshot()
    elif mutation == "cross_home":
        states[1]["home_id"] = "home-other"
    elif mutation == "unknown":
        states[1]["device_id"] = "missing-device"
    elif mutation == "bad_last":
        states[1]["reported_state"]["is_on"]["value"] = []
    elif mutation == "desired":
        states[1]["desired_state"] = {
            "revision": 1,
            "values": {"is_on": True},
            "report_baseline": None,
        }
    else:
        states[1]["private-key"] = "private-value"
    payload = {"schema_version": 1, "states": states}
    before = copy.deepcopy(payload)
    error(api, code, rebuild, store, states=payload)
    assert payload == before
    assert read(store).revision == read(store, device_id="device-two").revision == 0
    assert len(rebuild(store)) == 2


@pytest.mark.tc029_03
@pytest.mark.parametrize("initialize", ["put_one", "put_two", "rebuild"])
def test_rebuild_one_shot_and_home_isolation(api, store, initialize):
    if initialize == "put_one":
        put(store)
    elif initialize == "put_two":
        put(store, device_id="device-two", state=snapshot(device="device-two"))
    else:
        rebuild(store)
    before = read(store).to_dict()
    error(api, "already_initialized", rebuild, store)
    assert read(store).to_dict() == before
    views = rebuild(
        store,
        context("home-other"),
        home_id="home-other",
        states={
            "schema_version": 1,
            "states": [snapshot("home-other"), snapshot("home-other", "device-two")],
        },
    )
    assert len(views) == 2 and all(view.revision == 1 for view in views)
    assert read(store).to_dict() == before


@pytest.mark.tc029_03
def test_restart_and_empty_home_reconstruction(api):
    old = api.CurrentStateStore(**configuration())
    put(old)
    restarted = api.CurrentStateStore(**configuration())
    assert read(restarted, now_ms=0, max_age_ms=0).freshness == "uninitialized"
    assert read(restarted, now_ms=0, max_age_ms=0).revision == 0
    assert all(
        view.revision == 1 and view.updated_at_ms == 0 for view in rebuild(restarted, now_ms=0)
    )
    config = configuration()
    config["inventories"][0]["devices"] = []
    empty = api.CurrentStateStore(**config)
    assert rebuild(empty, states={"schema_version": 1, "states": []}) == ()
    error(api, "already_initialized", rebuild, empty, states={"schema_version": 1, "states": []})


@pytest.mark.tc029_04
def test_private_repr_serialization_and_canonical_diagnostics(api, store):
    assert repr(store) == "CurrentStateStore()"
    for clone in (pickle.dumps, copy.copy, copy.deepcopy):
        with pytest.raises(TypeError, match="state_store_serialization_forbidden"):
            clone(store)
    candidate = snapshot()
    candidate["reported_state"]["private-key"] = {"private": "private-value"}
    caught = error(api, "invalid_state", put, store, state=candidate)
    import traceback

    assert caught.path == ("state",) and caught.__suppress_context__
    assert "private-" not in "".join(traceback.format_exception(caught))
    assert read(store).revision == 0


@pytest.mark.tc029_04
def test_no_file_env_or_clock_dependency(api, monkeypatch):
    import builtins
    import os

    def deny(*args, **kwargs):
        pytest.fail("store attempted ambient I/O")

    monkeypatch.setattr(builtins, "open", deny)
    monkeypatch.setattr(os, "environ", {})
    store = api.CurrentStateStore(**configuration())
    assert put(store, now_ms=0).revision == 1
    assert read(store, now_ms=0, max_age_ms=0).freshness == "fresh"
    assert len(rebuild(api.CurrentStateStore(**configuration()), now_ms=0)) == 2


@pytest.mark.tc029_04
def test_installed_checks():
    assert check() == {"checks": 12, "offline": True}
