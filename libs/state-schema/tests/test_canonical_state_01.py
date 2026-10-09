"""TC-015-01: strict shapes, identity, errors and isolated domain records."""

import json
from copy import deepcopy
from dataclasses import FrozenInstanceError

import pytest
from state_support import changed, collection, error_at, order, state, state_required

pytestmark = state_required


@pytest.mark.parametrize("value", [False, True, 0, 0.0, -2, 3.5, "", "unknown"])
def test_round_trip(state_api, inventory, value):
    data = state()
    data["desired_state"]["values"]["power"] = value
    data["reported_state"]["power"]["value"] = value
    model = state_api.DeviceState.from_dict(data)
    batch = state_api.StateCollection.from_dict(collection(data), inventory=inventory)
    assert model.to_dict() == data
    assert state_api.validate_state(json.loads(json.dumps(model.to_dict()))) == data
    assert state_api.validate_states(batch.to_dict(), inventory=inventory) == collection(data)
    assert type(model.to_dict()["reported_state"]["power"]["value"]) is type(value)
    snapshot = model.to_dict()
    snapshot["reported_state"]["power"]["value"] = "changed"
    data["desired_state"]["values"]["power"] = "changed"
    assert model.to_dict()["reported_state"]["power"]["value"] == value
    assert model.to_dict()["desired_state"]["values"]["power"] == value
    with pytest.raises(FrozenInstanceError):
        model.home_id = "home-mutated"
    with pytest.raises(FrozenInstanceError):
        model.reported_state[0][1].status = "unknown"
    assert isinstance(model.reported_state, tuple)
    assert isinstance(model.desired_state.values, tuple)


@pytest.mark.parametrize("epoch,sequence", [(0, 0), (1, 0), (2**64, 2**64)])
def test_order_boundaries(state_api, epoch, sequence):
    assert state_api.Ordering.from_dict(order(sequence, epoch)).to_dict() == order(sequence, epoch)


@pytest.mark.parametrize(
    "path,value",
    [
        (("home_id",), ""),
        (("device_id",), "light.provider"),
        (("desired_state",), {}),
        (("desired_state", "revision"), True),
        (("desired_state", "revision"), 0),
        (("desired_state", "revision"), 1.0),
        (("desired_state", "values"), {}),
        (("desired_state", "values"), []),
        (("reported_state",), []),
        (("availability",), None),
        (("availability", "status"), "ONLINE"),
        (("reported_state", "power", "status"), "offline"),
        (("reported_state", "power", "value"), None),
        (("reported_state", "power", "ordering", "epoch"), True),
        (("reported_state", "power", "ordering", "epoch"), -1),
        (("reported_state", "power", "ordering", "sequence"), 1.0),
        (("reported_state", "power", "ordering", "sequence"), None),
    ],
)
def test_invalid_fields(state_api, path, value):
    data = changed(state(), path, value)
    expected = path if path != ("desired_state",) else ("desired_state", "revision")
    error_at(state_api, lambda: state_api.validate_state(data), expected)


@pytest.mark.parametrize("value", [None, [], {}, float("nan"), float("inf"), -float("inf")])
@pytest.mark.parametrize("branch", ["desired_state", "reported_state"])
def test_invalid_scalar(state_api, value, branch):
    path = (branch, "values", "power") if branch == "desired_state" else (branch, "power", "value")
    data = changed(state(), path, value)
    error_at(state_api, lambda: state_api.validate_state(data), path)


@pytest.mark.parametrize(
    "time",
    [
        "",
        "PRIVATE_DATE",
        "2026-01-01",
        "2026-01-01T12:00:00",
        "2026-01-01T12:00:00+00:00",
        "2026-01-01T12:00:60Z",
        "2026-02-29T12:00:00Z",
        "2026-13-01T12:00:00Z",
        "2026-01-01T24:00:00Z",
        "2026-01-01T12:00:00.Z",
        "2026-01-01T12:00:00.1234567Z",
        123,
        True,
    ],
)
@pytest.mark.parametrize("branch", ["report", "availability"])
def test_invalid_time(state_api, time, branch):
    path = (
        ("reported_state", "power", "observed_at")
        if branch == "report"
        else ("availability", "observed_at")
    )
    data = changed(state(), path, time)
    error_at(state_api, lambda: state_api.validate_state(data), path, private=("PRIVATE_DATE",))


@pytest.mark.parametrize(
    "time", ["2000-02-29T00:00:00Z", "2026-01-01T00:00:00.1Z", "2026-01-01T00:00:00.123456Z"]
)
def test_valid_time(state_api, time):
    data = changed(state(), ("reported_state", "power", "observed_at"), time)
    assert state_api.validate_state(data) == data


@pytest.mark.parametrize("branch", ["reported_state", "desired_state"])
@pytest.mark.parametrize("key", ["private.value", "", "Power", "1power", "x" * 65, "温度"])
def test_property_name_privacy(state_api, branch, key):
    data = state()
    parent = (
        data["desired_state"]["values"] if branch == "desired_state" else data["reported_state"]
    )
    parent[key] = parent.pop("power")
    path = (
        ("desired_state", "values", "<property>")
        if branch == "desired_state"
        else ("reported_state", "<property>")
    )
    error_at(state_api, lambda: state_api.validate_state(data), path, private=(key,) if key else ())


@pytest.mark.parametrize(
    "parent",
    [
        (),
        ("desired_state",),
        ("desired_state", "report_baseline"),
        ("reported_state", "power"),
        ("availability",),
        ("availability", "ordering"),
    ],
)
def test_missing_and_unknown_fields(state_api, parent):
    data = state()
    obj = data
    for key in parent:
        obj = obj[key]
    for field in list(obj):
        candidate = deepcopy(data)
        target = candidate
        for key in parent:
            target = target[key]
        del target[field]
        error_at(state_api, lambda: state_api.validate_state(candidate), (*parent, field))
    obj["PRIVATE_STRUCTURAL_KEY"] = "PRIVATE_PAYLOAD"
    error_at(
        state_api,
        lambda: state_api.validate_state(data),
        (*parent, "<unknown>"),
        private=("PRIVATE_STRUCTURAL_KEY", "PRIVATE_PAYLOAD"),
    )


@pytest.mark.parametrize("branch", ["report", "availability"])
def test_unknown_metadata_pairs(state_api, branch):
    data = state()
    obj = data["reported_state"]["power"] if branch == "report" else data["availability"]
    base = ("reported_state", "power") if branch == "report" else ("availability",)
    obj["status"] = "unknown"
    if branch == "report":
        obj["value"] = None
    assert state_api.validate_state(data) == data
    obj["observed_at"] = None
    error_at(state_api, lambda: state_api.validate_state(data), (*base, "observed_at"))
    obj["ordering"] = None
    assert state_api.validate_state(data) == data
    if branch == "report":
        obj["value"] = False
        error_at(state_api, lambda: state_api.validate_state(data), (*base, "value"))


@pytest.mark.parametrize("version", [True, 0, 2, 1.0, None, "1"])
def test_invalid_version(state_api, inventory, version):
    data = collection()
    data["schema_version"] = version
    error_at(
        state_api, lambda: state_api.validate_states(data, inventory=inventory), ("schema_version",)
    )


def test_collection_identity(state_api, inventory):
    original = deepcopy(inventory)
    assert state_api.validate_states(collection(), inventory=inventory) == collection()
    data = state()
    data["device_id"] = "unknown-device"
    assert state_api.validate_state(data) == data
    for identifier in ["unknown-device", inventory["home"]["id"], inventory["areas"][0]["id"]]:
        data["device_id"] = identifier
        error_at(
            state_api,
            lambda: state_api.validate_states(collection(data), inventory=inventory),
            ("states", 0, "device_id"),
        )
    data = state()
    data["home_id"] = "other-home"
    error_at(
        state_api,
        lambda: state_api.validate_states(collection(data), inventory=inventory),
        ("states", 0, "home_id"),
    )
    error_at(
        state_api,
        lambda: state_api.validate_states(collection(state(), state()), inventory=inventory),
        ("states", 1, "device_id"),
    )
    assert inventory == original
    private_inventory = deepcopy(inventory)
    private_inventory["devices"][0]["area_id"] = "private-invalid-area"
    error_at(
        state_api,
        lambda: state_api.validate_states(collection(), inventory=private_inventory),
        ("inventory", "devices", 0, "area_id"),
        private=("private-invalid-area",),
    )


@pytest.mark.parametrize("parent", [(), ("desired_state",), ("reported_state",), ("availability",)])
@pytest.mark.parametrize("value", [None, [], "private-input", 0, False])
def test_wrong_object_shapes(state_api, parent, value):
    data = value if not parent else changed(state(), parent, value)
    if parent == ("desired_state",) and value is None:
        assert state_api.validate_state(data)["desired_state"] is None
    else:
        error_at(
            state_api, lambda: state_api.validate_state(data), parent, private=("private-input",)
        )


@pytest.mark.parametrize("field", ["observed_at", "ordering"])
@pytest.mark.parametrize("branch", ["report", "availability"])
def test_required_metadata(state_api, field, branch):
    base = ("reported_state", "power") if branch == "report" else ("availability",)
    data = changed(state(), (*base, field), None)
    error_at(state_api, lambda: state_api.validate_state(data), (*base, field))


@pytest.mark.parametrize(
    "name,value,path",
    [
        ("Ordering", {"epoch": 0, "sequence": True}, ("sequence",)),
        (
            "Observation",
            {"status": "known", "value": [], "observed_at": None, "ordering": None},
            ("value",),
        ),
        (
            "Availability",
            {"status": "offline", "observed_at": None, "ordering": None},
            ("observed_at",),
        ),
        ("DesiredState", {"revision": 0, "values": {}, "report_baseline": None}, ("revision",)),
    ],
)
def test_nested_external_factories(state_api, name, value, path):
    error_at(state_api, lambda: getattr(state_api, name).from_dict(value), path)


@pytest.mark.parametrize(
    "data,path",
    [
        ({"schema_version": 1, "states": None}, ("states",)),
        ({"states": []}, ("schema_version",)),
        ({"schema_version": 1}, ("states",)),
        ({"schema_version": 1, "states": [], "PRIVATE_FIELD": True}, ("<unknown>",)),
        ([], ()),
    ],
)
def test_collection_envelope(state_api, inventory, data, path):
    error_at(
        state_api,
        lambda: state_api.validate_states(data, inventory=inventory),
        path,
        private=("PRIVATE_FIELD",),
    )


def test_inventory_and_binding_remain_separate(state_api, api, binding_api, inventory):
    from binding_support import binding

    original = deepcopy(inventory)
    data = state()
    assert state_api.validate_states(collection(data), inventory=inventory)
    assert inventory == original
    embedded = deepcopy(inventory)
    embedded["devices"][0]["reported_state"] = data["reported_state"]
    with pytest.raises(api.InventoryError):
        api.validate_inventory(embedded)
    mapping = binding()
    mapping["availability"] = data["availability"]
    with pytest.raises(binding_api.BindingError):
        binding_api.validate_binding(mapping)


@pytest.mark.parametrize("branch", ["home", "device", "root"])
def test_inventory_arbitrary_key_privacy(state_api, binding_api, inventory, branch):
    from binding_support import binding
    from binding_support import collection as binding_collection

    private = "PRIVATE_INVENTORY_KEY"
    data = deepcopy(inventory)
    target = {"home": data["home"], "device": data["devices"][0], "root": data}[branch]
    target[private] = "PRIVATE_INVENTORY_VALUE"
    base = {"home": ("home",), "device": ("devices", 0), "root": ()}[branch]
    error_at(
        state_api,
        lambda: state_api.validate_states(collection(state()), inventory=data),
        ("inventory", *base, "<unknown>"),
        private=(private, "PRIVATE_INVENTORY_VALUE"),
    )
    with pytest.raises(binding_api.BindingError) as caught:
        binding_api.validate_bindings(binding_collection(binding()), inventory=data)
    assert caught.value.path == ("inventory", *base, "<unknown>")
    assert private not in str(caught.value)
    assert private not in repr(caught.value)


@pytest.mark.parametrize("hour,minute,second", [(24, 0, 0), (23, 60, 0), (23, 59, 60)])
def test_explicit_clock_ranges_before_parser(state_api, monkeypatch, hour, minute, second):
    class PermissiveParser:
        @staticmethod
        def fromisoformat(value):
            pytest.fail("Invalid clock range reached the interpreter parser")

    monkeypatch.setattr(state_api, "datetime", PermissiveParser)
    time = f"2026-01-01T{hour:02}:{minute:02}:{second:02}Z"
    data = changed(state(), ("reported_state", "power", "observed_at"), time)
    error_at(
        state_api,
        lambda: state_api.validate_state(data),
        ("reported_state", "power", "observed_at"),
    )


def test_canonical_id_pattern_has_one_authority(api, binding_api, state_api):
    assert binding_api.CANONICAL_ID_PATTERN is api.CANONICAL_ID_PATTERN
    assert state_api.CANONICAL_ID_PATTERN is api.CANONICAL_ID_PATTERN
