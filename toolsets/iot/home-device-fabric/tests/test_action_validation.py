"""REQ-037 generator proposals: independent criteria/review remain pending."""
import copy
import json
import pickle
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError

import pytest
from action_validation_artifact_smoke import configuration, request
from home_device_fabric.action_validation import ActionValidationError, ActionValidator
from home_device_fabric.ha_mapping import _json
from home_device_fabric.mock import MockProvider


@pytest.fixture(autouse=True)
def no_provider_calls(monkeypatch):
    calls = []

    def deny(*args, **kwargs):
        calls.append(1)
        raise AssertionError("provider call forbidden")

    for name in ("discover", "snapshot", "submit", "advance", "settle"):
        monkeypatch.setattr(MockProvider, name, deny)
    yield calls
    assert calls == [], "provider call attempted even if swallowed"


@pytest.fixture
def validator():
    return ActionValidator(**configuration())


@pytest.mark.tc037_01
@pytest.mark.parametrize("changes,code", [
    ({"home_id": "home-other", "device_id": "missing"}, "unknown_home"),
    ({"device_id": "missing", "capability_id": "vendor.private"}, "unknown_device"),
    ({"device_id": "device-7"}, "capabilities_uninitialized"),
    ({"device_id": "device-6"}, "unknown_capability"),
    ({"device_id": "device-1"}, "unknown_capability"),
    ({"capability_id": "vendor.private"}, "unknown_capability"),
    ({"capability_version": 2}, "unsupported_capability_version"),
    ({"action_id": "toggle"}, "unknown_action"),
    ({"action_id": "unlock"}, "unknown_action"),
    ({"action_id": "set_on", "arguments": {"vendor": "secret"}}, "invalid_arguments"),
])
def test_ordered_selection_and_zero_provider_calls(validator, changes, code, offline):
    raw = request(**changes)
    before = copy.deepcopy(raw)
    result = validator.validate(raw)
    assert result.to_dict() == {"status": "rejected", "failure_code": code, "request": None}
    assert raw == before and offline == []


@pytest.mark.tc037_01
def test_exact_supported_revisions_never_fallback():
    config = configuration()
    descriptor = copy.deepcopy(config["capabilities"][0]["capabilities"][0])
    descriptor["capability_version"] = 2
    config["capabilities"][0]["capabilities"].append(descriptor)
    validator = ActionValidator(**config)
    for version in (1, 2):
        raw = request(capability_version=version)
        assert validator.validate(raw).to_dict()["request"] == raw
    assert validator.validate(request(capability_version=3)).failure_code == (
        "unsupported_capability_version")


@pytest.mark.tc037_02
@pytest.mark.parametrize("value", [True, False])
def test_valid_switch_preserves_exact_request(validator, value):
    raw = request(arguments={"is_on": value})
    assert validator.validate(raw).to_dict() == {
        "status": "valid", "failure_code": None, "request": raw}


@pytest.mark.tc037_02
@pytest.mark.parametrize("value", [0, 50, 100])
def test_valid_curtain_range_boundaries(validator, value):
    raw = request(device_id="device-1", capability_id="home.positionable",
                  action_id="set_position", arguments={"position_percent": value})
    assert validator.validate(raw).to_dict()["request"] == raw


@pytest.mark.tc037_02
@pytest.mark.parametrize("arguments", [{}, {"is_on": 0}, {"is_on": 1}, {"is_on": "true"},
    {"is_on": None}, {"is_on": []}, {"is_on": {}}, {"is_on": True, "secret": "private"}])
def test_switch_arguments_not_coerced(validator, arguments):
    assert validator.validate(request(arguments=arguments)).failure_code == "invalid_arguments"


@pytest.mark.tc037_02
@pytest.mark.parametrize("value", [-1, 101, 0.0, 50.5, True, False, "50", None])
def test_curtain_does_not_round_coerce_or_accept_out_of_range(validator, value):
    result = validator.validate(request(device_id="device-1", capability_id="home.positionable",
        action_id="set_position", arguments={"position_percent": value}))
    assert result.failure_code == "invalid_arguments"


@pytest.mark.tc037_02
@pytest.mark.parametrize("i,capability", list(enumerate(("home.temperature_sensor",
    "home.humidity_sensor", "home.power_meter", "home.battery_powered"), start=2)))
@pytest.mark.parametrize("action", ["set_value", "set_on", "unlock"])
def test_all_read_only_sensors_reject_every_write(validator, i, capability, action):
    result = validator.validate(request(device_id=f"device-{i}", capability_id=capability,
                                        action_id=action))
    assert result.failure_code == "read_only_capability" and result.to_dict()["request"] is None


@pytest.mark.tc037_03
@pytest.mark.parametrize("field,value", [("schema_version", True), ("schema_version", 2),
    ("home_id", " bad "), ("device_id", 1), ("capability_version", True),
    ("capability_version", 0), ("action_id", "private.action"), ("arguments", []),
    ("arguments", None), ("arguments", {"value": float("nan")}),
    ("arguments", {"value": float("inf")}), ("trace_id", ""), ("idempotency_key", 1)])
def test_malformed_canonical_request_rejected_before_lookup(validator, field, value):
    assert validator.validate(request(**{field: value})).failure_code == "invalid_request"


@pytest.mark.tc037_03
@pytest.mark.parametrize("kind", ["missing", "extra", "object", "cycle", "alias", "depth",
                                   "integer", "nonstring_key", "typed_record"])
def test_hostile_json_shapes_have_fixed_diagnostics(validator, kind):
    raw = request()
    if kind == "missing":
        del raw["arguments"]
    elif kind == "extra":
        raw["private-secret"] = "secret"
    elif kind == "object":
        raw = object()
    elif kind == "cycle":
        raw["arguments"]["secret"] = raw
    elif kind == "alias":
        shared = []
        raw["arguments"] = {"one": shared, "two": shared}
    elif kind == "depth":
        nested = {}
        for _ in range(40):
            nested = {"secret": nested}
        raw["arguments"] = nested
    elif kind == "integer":
        raw["arguments"] = {"value": 1 << 5000}
    elif kind == "nonstring_key":
        raw["arguments"] = {1: "secret"}
    else:
        from state_schema.action_contracts import ActionRequest
        raw = ActionRequest.from_dict(raw)
    result = validator.validate(raw)
    assert result.failure_code == "invalid_request"
    assert "secret" not in json.dumps(result.to_dict()) + repr(result)


@pytest.mark.tc037_03
def test_byte_limit_is_exact_canonical_utf8():
    raw = request()
    size = len(_json(raw).encode("utf-8"))
    assert ActionValidator(**configuration(), max_input_bytes=size).validate(raw).status == "valid"
    smaller = ActionValidator(**configuration(), max_input_bytes=size - 1)
    assert smaller.validate(raw).failure_code == "input_too_large"
    # UTF-8 characters in an extra field still hit the byte budget before shape diagnostics.
    raw["extra"] = "温度" * 100
    assert ActionValidator(**configuration(), max_input_bytes=size).validate(raw).failure_code == (
        "input_too_large")


@pytest.mark.tc037_03
@pytest.mark.parametrize("kind", ["bad_inventory", "unknown_home", "unknown_device", "duplicate",
    "duplicate_capability", "bad_descriptor", "mapping", "list", "aliased", "bool_limit",
    "zero_limit", "huge_limit", "subclass_limit"])
def test_configuration_rejected_without_exception_payloads(kind):
    config = configuration()
    if kind == "bad_inventory":
        config["registered_inventory"]["private-secret"] = "secret"
    elif kind in ("unknown_home", "unknown_device"):
        config["capabilities"][0]["home_id" if kind == "unknown_home" else "device_id"] = "secret"
    elif kind == "duplicate":
        config["capabilities"].append(copy.deepcopy(config["capabilities"][0]))
    elif kind == "duplicate_capability":
        caps = config["capabilities"][0]["capabilities"]
        caps.append(copy.deepcopy(caps[0]))
    elif kind == "bad_descriptor":
        config["capabilities"][0]["capabilities"][0]["private-secret"] = "secret"
    elif kind == "mapping":
        config["capabilities"][0]["provider_mapping"] = "secret"
    elif kind == "list":
        config["capabilities"] = {}
    elif kind == "aliased":
        config["capabilities"].append(config["capabilities"][0])
    else:
        class Integer(int):
            pass
        config["max_input_bytes"] = {"bool_limit": True, "zero_limit": 0,
            "huge_limit": 16777217, "subclass_limit": Integer(1000)}[kind]
    with pytest.raises(ActionValidationError, match="^invalid_configuration$") as caught:
        ActionValidator(**config)
    assert caught.value.__context__ is None and caught.value.__cause__ is None
    assert "secret" not in repr(caught.value)


@pytest.mark.tc037_03
def test_configuration_and_result_detachment_and_immutability():
    config = configuration()
    validator = ActionValidator(**config)
    config["capabilities"].clear()
    config["registered_inventory"]["devices"].clear()
    raw = request()
    result = validator.validate(raw)
    raw["arguments"]["is_on"] = False
    exported = result.to_dict()
    exported["request"]["arguments"]["is_on"] = False
    assert result.to_dict()["request"]["arguments"]["is_on"] is True
    assert validator.validate(request()).status == "valid"
    for obj, attr in ((validator, "_home"), (result, "failure_code")):
        with pytest.raises(FrozenInstanceError):
            setattr(obj, attr, "secret")
    with pytest.raises(AttributeError, match="immutable_action_validator"):
        validator.__init__(**configuration())


@pytest.mark.tc037_03
@pytest.mark.parametrize("copier", [copy.copy, copy.deepcopy, pickle.dumps])
def test_serialization_redacted_for_valid_rejected_and_validator(validator, copier):
    for obj, message in ((validator, "action_validator_serialization_forbidden"),
        (validator.validate(request()), "action_validation_result_serialization_forbidden"),
        (validator.validate(request(action_id="unlock")),
         "action_validation_result_serialization_forbidden")):
        with pytest.raises(TypeError, match="^" + message + "$"):
            copier(obj)
        assert "home-example" not in repr(obj)


@pytest.mark.tc037_03
def test_isolation_and_concurrent_calls(validator):
    other = configuration()
    other["capabilities"] = []
    empty = ActionValidator(**other)
    def validate(i):
        return (validator if i % 2 else empty).validate(request()).failure_code
    with ThreadPoolExecutor(max_workers=4) as pool:
        codes = list(pool.map(validate, range(100)))
    assert codes == [None if i % 2 else "capabilities_uninitialized" for i in range(100)]


@pytest.mark.tc037_04
def test_smoke_contract_offline(offline):
    from action_validation_artifact_smoke import check
    assert check() == {"checks": 22, "offline": True}
    assert offline == []


@pytest.mark.tc037_02
def test_read_only_descriptor_cannot_enable_sensor_setter():
    config = configuration()
    sensor = config["capabilities"][2]["capabilities"][0]
    sensor["actions"] = {"set_value": {
        "title": "Misconfigured setter", "description": "Must not enable sensor writes",
        "input_schema": {"type": "object", "properties": {}, "required": [],
                         "additionalProperties": False},
        "output_schema": {"type": "null"}, "risk": "medium", "timeout_ms": 1000,
        "idempotency": "safe_repeat", "completion_policy": {"kind": "ack_only"}}}
    result = ActionValidator(**config).validate(request(device_id="device-2",
        capability_id="home.temperature_sensor", action_id="set_value", arguments={}))
    assert result.failure_code == "read_only_capability"


@pytest.mark.tc037_01
def test_writable_descriptor_without_actions_returns_unknown_action():
    config = configuration()
    config["capabilities"][0]["capabilities"][0]["actions"] = {}
    assert ActionValidator(**config).validate(request()).failure_code == "unknown_action"
