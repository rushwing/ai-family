"""REQ-034 literal query, authorization, freshness and concurrency checks."""

import copy
import importlib
import pickle
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError

import pytest
from home_queries_artifact_smoke import configuration, context
from state_store_artifact_smoke import snapshot


@pytest.fixture
def api():
    return importlib.import_module("home_device_fabric.home_queries")


@pytest.fixture
def setup(api):
    store_api = importlib.import_module("home_device_fabric.state_store")
    catalogue = importlib.import_module(
        "state_schema.initial_capabilities"
    ).load_initial_capabilities()
    store = store_api.CurrentStateStore(**configuration())
    descriptor = catalogue.get("home.switchable", 1).to_dict()
    metadata = [
        {"home_id": "home-example", "device_id": "device-one", "capabilities": [descriptor]},
        {"home_id": "home-other", "device_id": "device-one", "capabilities": []},
    ]
    return store, api.HomeQueryService(store=store, capabilities=metadata), metadata


def call(service, method, caller=None, **kwargs):
    args = {"home_id": "home-example"}
    if method in ("device", "state", "capabilities"):
        args["device_id"] = "device-one"
    if method in ("state", "states"):
        args.update(now_ms=100, max_age_ms=10)
    args.update(kwargs)
    return getattr(service, method)(context() if caller is None else caller, **args)


def fail(api, code, function, *args, **kwargs):
    with pytest.raises(api.HomeQueryError) as caught:
        function(*args, **kwargs)
    error = caught.value
    assert error.code == code
    assert error.to_dict() == {"code": code}
    assert error.__context__ is None and error.__cause__ is None
    assert str(error) == code
    return error


@pytest.mark.tc034_01
@pytest.mark.parametrize("method", ["home", "areas", "devices", "device"])
def test_literal_inventory_projection(setup, method):
    _, service, _ = setup
    inv = configuration()["inventories"][0]
    expected = {
        "home": inv["home"],
        "areas": [{**row, "aliases": [], "labels": []} for row in inv["areas"]],
        "devices": [{**row, "labels": []} for row in reversed(inv["devices"])],
        "device": {**inv["devices"][1], "labels": []},
    }
    assert call(service, method).to_dict() == {"status": "found", "data": expected[method]}


@pytest.mark.tc034_01
@pytest.mark.parametrize(
    "area,expected",
    [
        ("area-main", ["device-one"]),
        ("area-empty", []),
        (None, ["device-one", "device-two"]),
    ],
)
def test_area_filters(setup, area, expected):
    result = call(setup[1], "devices", area_id=area).to_dict()
    assert result["status"] == "found"
    assert [row["id"] for row in result["data"]] == expected


@pytest.mark.tc034_01
def test_canonical_descriptors_detached_and_ordered(api, setup):
    store, _, metadata = setup
    catalogue = importlib.import_module(
        "state_schema.initial_capabilities"
    ).load_initial_capabilities()
    temperature = catalogue.get("home.temperature_sensor", 1).to_dict()
    switch = copy.deepcopy(metadata[0]["capabilities"][0])
    metadata[0]["capabilities"] = [temperature, switch]
    service = api.HomeQueryService(store=store, capabilities=metadata)
    assert call(service, "capabilities").to_dict() == {
        "status": "found",
        "data": [switch, temperature],
    }
    metadata[0]["capabilities"].clear()
    assert len(call(service, "capabilities").to_dict()["data"]) == 2
    assert call(
        service, "capabilities", caller=context("home-other"), home_id="home-other"
    ).to_dict() == {"status": "found", "data": []}


@pytest.mark.tc034_02
@pytest.mark.parametrize(
    "method", ["home", "areas", "devices", "device", "state", "states", "capabilities"]
)
@pytest.mark.parametrize(
    "change",
    [
        {"subject_id": "subject-denied"},
        {"family_member_id": "member-denied"},
        {"role": "kid"},
        {"home_id": "home-other"},
        {"home_id": "home-absent"},
    ],
)
def test_every_entry_denies_before_lookup(api, setup, method, change):
    caller = {**context(), **change}
    # Invalid selectors and time must not reveal validation or membership first.
    extra = {}
    if method in ("device", "state", "capabilities"):
        extra["device_id"] = {"private-id": "secret"}
    if method == "devices":
        extra["area_id"] = []
    if method in ("state", "states"):
        extra.update(now_ms=-1, max_age_ms=True)
    fail(api, "forbidden", call, setup[1], method, caller=caller, **extra)


@pytest.mark.tc034_02
@pytest.mark.parametrize(
    "method", ["home", "areas", "devices", "device", "state", "states", "capabilities"]
)
@pytest.mark.parametrize(
    "caller", [context(member="member-reader"), context(member="member-child", role="kid")]
)
def test_read_grants_on_every_entry(setup, method, caller):
    assert call(setup[1], method, caller=caller).status == "found"


@pytest.mark.tc034_02
@pytest.mark.parametrize(
    "caller", [None, {}, {**context(), "role": "root"}, {**context(), "private-token": "secret"}]
)
def test_invalid_context(api, setup, caller):
    fail(api, "invalid_context", setup[1].home, caller, home_id="home-example")


@pytest.mark.tc034_02
@pytest.mark.parametrize("home", ["home-other", "home-absent", None, True, {}])
def test_target_home_scope(api, setup, home):
    fail(api, "forbidden", call, setup[1], "home", home_id=home)


@pytest.mark.tc034_03
@pytest.mark.parametrize(
    "method,kwargs",
    [
        ("device", {"device_id": "device-absent"}),
        ("state", {"device_id": "device-absent"}),
        ("capabilities", {"device_id": "device-absent"}),
        ("devices", {"area_id": "area-absent"}),
    ],
)
def test_not_found(setup, method, kwargs):
    assert call(setup[1], method, **kwargs).to_dict() == {"status": "not_found", "data": None}


@pytest.mark.tc034_03
def test_metadata_never_creates_inventory(api, setup):
    store, _, metadata = setup
    metadata.append({"home_id": "home-example", "device_id": "device-absent", "capabilities": []})
    service = api.HomeQueryService(store=store, capabilities=metadata)
    assert call(service, "capabilities", device_id="device-absent").status == "not_found"
    assert call(service, "capabilities", device_id="device-two").to_dict() == {
        "status": "uninitialized",
        "data": None,
    }


@pytest.mark.tc034_03
def test_uninitialized_never_invents_state(setup):
    result = call(setup[1], "state").to_dict()
    assert result == {
        "status": "found",
        "data": {
            "status": "found",
            "state": {
                "home_id": "home-example",
                "device_id": "device-one",
                "desired_state": None,
                "reported_state": {},
                "availability": {"status": "unknown", "observed_at": None, "ordering": None},
            },
            "revision": 0,
            "updated_at_ms": None,
            "freshness": "uninitialized",
        },
    }


@pytest.mark.tc034_03
@pytest.mark.parametrize(
    "now,age,expected",
    [(100, 0, "fresh"), (110, 10, "fresh"), (111, 10, "stale"), (1000, 0, "stale")],
)
@pytest.mark.parametrize("method", ["state", "states"])
def test_exact_freshness_and_false_observation(setup, now, age, expected, method):
    store, service, _ = setup
    value = snapshot(value=False)
    store.put(
        context(),
        home_id="home-example",
        device_id="device-one",
        state=value,
        expected_revision=0,
        now_ms=100,
    )
    result = call(service, method, now_ms=now, max_age_ms=age).to_dict()["data"]
    view = result if method == "state" else result[0]
    assert view == {
        "status": "found",
        "state": value,
        "freshness": expected,
        "revision": 1,
        "updated_at_ms": 100,
    }


@pytest.mark.tc034_03
@pytest.mark.parametrize("method", ["state", "states"])
def test_clock_regression(api, setup, method):
    store, service, _ = setup
    store.put(
        context(),
        home_id="home-example",
        device_id="device-one",
        state=snapshot(),
        expected_revision=0,
        now_ms=100,
    )
    fail(api, "clock_regression", call, service, method, now_ms=99)


@pytest.mark.tc034_03
@pytest.mark.parametrize(
    "method", ["home", "areas", "devices", "device", "state", "states", "capabilities"]
)
def test_result_detachment_and_no_write(setup, method):
    store, service, _ = setup
    before = store.snapshot(context(), home_id="home-example", now_ms=100, max_age_ms=10)
    result = call(service, method)
    expected = result.to_dict()
    output = result.to_dict()
    if type(output["data"]) is list:
        output["data"].clear()
    else:
        output["data"].clear()
    assert result.to_dict() == expected == call(service, method).to_dict()
    assert before == store.snapshot(context(), home_id="home-example", now_ms=100, max_age_ms=10)


@pytest.mark.tc034_03
def test_atomic_snapshots_during_rebuild(setup):
    store, service, _ = setup

    def rebuild():
        for index in range(1):
            rows = [
                snapshot(device=device, value=bool(index % 2))
                for device in ("device-one", "device-two")
            ]
            store.rebuild(
                context(),
                home_id="home-example",
                now_ms=100,
                states={"schema_version": 1, "states": rows},
            )

    def query():
        for _ in range(100):
            rows = call(service, "states").to_dict()["data"]
            assert len(rows) == 2
            assert rows[0]["revision"] == rows[1]["revision"]
            assert rows[0]["state"]["reported_state"] == rows[1]["state"]["reported_state"]

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(rebuild), pool.submit(query), pool.submit(query)]
        for future in futures:
            future.result()


@pytest.mark.tc034_04
@pytest.mark.parametrize(
    "method,selector",
    [
        ("device", "device_id"),
        ("state", "device_id"),
        ("capabilities", "device_id"),
        ("devices", "area_id"),
    ],
)
@pytest.mark.parametrize("value", ["", "provider.entity", "secret token", True, [], {}])
def test_invalid_selectors(api, setup, method, selector, value):
    fail(api, "invalid_selector", call, setup[1], method, **{selector: value})


@pytest.mark.tc034_04
@pytest.mark.parametrize("method", ["state", "states"])
@pytest.mark.parametrize("field", ["now_ms", "max_age_ms"])
@pytest.mark.parametrize("value", [-1, True, 1.5, "100", None])
def test_invalid_time(api, setup, method, field, value):
    fail(api, "invalid_time", call, setup[1], method, **{field: value})


@pytest.mark.tc034_04
@pytest.mark.parametrize(
    "mutation",
    [
        "not_list",
        "bad_record",
        "extra_key",
        "missing_key",
        "bad_home",
        "bad_device",
        "duplicate_record",
        "bad_descriptors",
        "duplicate_descriptor",
        "provider_mapping",
        "bad_descriptor",
        "nonfinite",
        "alias",
        "cycle",
        "depth",
        "nodes",
        "bytes",
        "surrogate",
    ],
)
def test_invalid_configuration_redacted(api, setup, mutation):
    store, _, metadata = setup
    raw = copy.deepcopy(metadata)
    if mutation == "not_list":
        raw = {}
    elif mutation == "bad_record":
        raw = [None]
    elif mutation == "extra_key":
        raw[0]["private-secret"] = "secret"
    elif mutation == "missing_key":
        del raw[0]["home_id"]
    elif mutation == "bad_home":
        raw[0]["home_id"] = "secret token"
    elif mutation == "bad_device":
        raw[0]["device_id"] = True
    elif mutation == "duplicate_record":
        raw.append(copy.deepcopy(raw[0]))
    elif mutation == "bad_descriptors":
        raw[0]["capabilities"] = {}
    elif mutation == "duplicate_descriptor":
        raw[0]["capabilities"].append(copy.deepcopy(raw[0]["capabilities"][0]))
    elif mutation == "provider_mapping":
        raw[0]["capabilities"][0]["entity_id"] = "switch.secret"
    elif mutation == "bad_descriptor":
        raw[0]["capabilities"] = [{}]
    elif mutation == "nonfinite":
        raw[0]["capabilities"] = [float("nan")]
    elif mutation == "alias":
        raw.append(raw[0])
    elif mutation == "cycle":
        raw.append(raw)
    elif mutation == "depth":
        raw = []
        for _ in range(34):
            raw = [raw]
    elif mutation == "nodes":
        raw = [None] * 200001
    elif mutation == "bytes":
        raw = ["x" * (16 * 1024 * 1024 + 1)]
    elif mutation == "surrogate":
        raw = ["\ud800"]
    fail(api, "invalid_configuration", api.HomeQueryService, store=store, capabilities=raw)


@pytest.mark.tc034_04
@pytest.mark.parametrize("bad_store", [None, {}, "private-store"])
def test_invalid_store(api, bad_store):
    fail(api, "invalid_configuration", api.HomeQueryService, store=bad_store, capabilities=[])


@pytest.mark.tc034_04
def test_no_reinitialization_or_serialization(api, setup):
    store, service, _ = setup
    result = call(service, "home")
    for obj in (service, result):
        assert "home-example" not in repr(obj)
        for function in (pickle.dumps, copy.copy, copy.deepcopy):
            with pytest.raises(TypeError):
                function(obj)
        with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
            obj._payload = "private"
    with pytest.raises(AttributeError):
        service.__init__(store=store, capabilities=[])
    with pytest.raises(AttributeError):
        result.__init__("found", {})


@pytest.mark.tc034_04
@pytest.mark.parametrize("exception", [KeyboardInterrupt, SystemExit])
def test_process_control_not_swallowed(api, setup, monkeypatch, exception):
    def interrupt(value):
        raise exception()

    monkeypatch.setattr(api, "_json", interrupt)
    with pytest.raises(exception):
        api.HomeQueryService(store=setup[0], capabilities=[])


@pytest.mark.tc034_03
@pytest.mark.parametrize("availability", ["online", "offline", "unknown"])
def test_availability_and_intent_remain_separate(setup, availability):
    store, service, _ = setup
    value = snapshot(value=False)
    value["desired_state"] = {
        "revision": 1,
        "values": {"is_on": True},
        "report_baseline": {"epoch": 1, "sequence": 0},
    }
    value["availability"]["status"] = availability
    store.put(
        context(),
        home_id="home-example",
        device_id="device-one",
        state=value,
        expected_revision=0,
        now_ms=100,
    )
    result = call(service, "state", now_ms=111).to_dict()["data"]
    assert result["state"] == value
    assert result["freshness"] == "stale"
    assert result["state"]["reported_state"]["is_on"]["value"] is False
    assert result["state"]["desired_state"]["values"]["is_on"] is True


@pytest.mark.tc034_01
def test_accepted_mapper_inference_store_query_integration(api):
    from home_device_fabric.ha_capabilities import HACapabilityInferrer
    from home_device_fabric.ha_mapping import HARegistryMapper
    from home_device_fabric.state_store import CurrentStateStore

    config = {
        "schema_version": 1,
        "home": {"id": "home-example", "name": "Example", "residence_type": "other"},
        "provider_instance_id": "ha-example",
        "area_ids": {},
        "device_ids": {"private-provider-id": "device-one"},
        "entity_ids": {},
    }
    discovery = {
        "devices": [{"id": "private-provider-id"}],
        "areas": [],
        "entities": [{"entity_id": "switch.private", "device_id": "private-provider-id"}],
        "states": [{"entity_id": "switch.private", "state": "off", "attributes": {}}],
    }
    mapped = HARegistryMapper(config).map(discovery).for_adapter()
    inferred = (
        HACapabilityInferrer(provider_instance_id="ha-example")
        .infer(**mapped, discovery=discovery)
        .for_adapter()
    )
    metadata = [
        {
            "home_id": row["home_id"],
            "device_id": row["device_id"],
            "capabilities": [item["descriptor"] for item in row["capabilities"]],
        }
        for row in inferred["devices"]
    ]
    store = CurrentStateStore(
        inventories=[mapped["inventory"]], grants=[{**context(), "access": "read"}]
    )
    service = api.HomeQueryService(store=store, capabilities=metadata)
    import json

    result = call(service, "capabilities").to_dict()
    assert [item["capability_id"] for item in result["data"]] == ["home.switchable"]
    assert "private" not in json.dumps(result) and "provider_mapping" not in json.dumps(result)
    # Inference metadata cannot fabricate the switch's reported observation.
    assert call(service, "state").to_dict()["data"]["state"]["reported_state"] == {}
    fail(
        api,
        "invalid_configuration",
        api.HomeQueryService,
        store=store,
        capabilities=inferred["devices"],
    )


@pytest.mark.tc034_02
@pytest.mark.parametrize("method", ["inventory", "snapshot"])
def test_store_read_extensions_enforce_grants(setup, method):
    from home_device_fabric.state_store import StateStoreError

    kwargs = {"home_id": "home-example"}
    if method == "snapshot":
        kwargs.update(now_ms=0, max_age_ms=0)
    with pytest.raises(StateStoreError) as caught:
        getattr(setup[0], method)(context(member="member-denied"), **kwargs)
    assert caught.value.code == "forbidden"


@pytest.mark.tc034_03
def test_store_snapshot_holds_read_lock(setup, monkeypatch):
    # Concurrent writer cannot alter later rows while one snapshot materializes.
    from home_device_fabric import state_store as module

    store, service, _ = setup
    original = module._Stored.view
    observed = []

    def view(row, now, age):
        observed.append(store._lock.locked())
        return original(row, now, age)

    monkeypatch.setattr(module._Stored, "view", view)
    call(service, "states")
    assert observed == [True, True]


@pytest.mark.tc034_04
def test_queries_perform_no_file_environment_or_datetime_io(setup, monkeypatch):
    import builtins
    import datetime
    import io
    import os
    from pathlib import Path

    class NoClock:
        @classmethod
        def now(cls, *args, **kwargs):
            raise AssertionError("ambient datetime forbidden")

    def denied(*args, **kwargs):
        raise AssertionError("ambient I/O forbidden")

    store, service, metadata = setup
    api = importlib.import_module("home_device_fabric.home_queries")
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", denied)
        patch.setattr(io, "open", denied)
        patch.setattr(Path, "open", denied)
        patch.setattr(os, "environ", None)
        patch.setattr(datetime, "datetime", NoClock)
        service = api.HomeQueryService(store=store, capabilities=metadata)
        for method in ("home", "areas", "devices", "device", "state", "states", "capabilities"):
            assert call(service, method).status == "found"


@pytest.mark.tc034_04
@pytest.mark.parametrize("exception", [KeyboardInterrupt, SystemExit])
def test_store_process_control_propagates(api, setup, monkeypatch, exception):
    def interrupt(*args, **kwargs):
        raise exception()

    monkeypatch.setattr(type(setup[0]), "inventory", interrupt)
    with pytest.raises(exception):
        call(setup[1], "home")


@pytest.mark.tc034_03
def test_empty_home_has_found_empty_collections(api):
    from home_device_fabric.state_store import CurrentStateStore

    config = configuration()
    config["inventories"][0]["devices"] = []
    config["inventories"][0]["areas"] = []
    service = api.HomeQueryService(store=CurrentStateStore(**config), capabilities=[])
    for method in ("areas", "devices", "states"):
        assert call(service, method).to_dict() == {"status": "found", "data": []}
    assert call(service, "device").status == "not_found"
