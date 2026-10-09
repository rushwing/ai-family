"""TC-016-04: references and exact structural schema compatibility."""

from copy import deepcopy

import pytest
from capability_support import capability_required, descriptor, reject

pytestmark = capability_required


@pytest.mark.parametrize(
    "policy",
    [
        {"kind": "ack_only"},
        {"kind": "event_confirmed", "event": "changed"},
        {"kind": "state_converged", "targets": {"power": {"source": "constant", "value": False}}},
        {"kind": "state_converged", "targets": {"power": {"source": "input", "field": "power"}}},
    ],
)
def test_valid_policies(capability_api, policy):
    data = descriptor()
    data["actions"]["set_power"]["completion_policy"] = policy
    assert capability_api.validate_capability(data) == data


@pytest.mark.parametrize(
    "policy",
    [
        {"kind": "event_confirmed", "event": "absent"},
        {"kind": "event_confirmed", "event": True},
        {"kind": "event_confirmed"},
        {"kind": "state_converged", "targets": {}},
        {"kind": "state_converged", "targets": {"absent": {"source": "constant", "value": False}}},
        *(
            {"kind": "state_converged", "targets": {"power": source}}
            for source in (
                {},
                {"source": "unknown"},
                {"source": "constant", "value": 0},
                {"source": "constant", "value": None},
                {"source": "constant"},
                {"source": "input", "field": "absent"},
                {"source": "input", "field": 1},
                {"source": "input", "field": "power", "value": False},
                {"source": "constant", "value": False, "field": "power"},
                {"source": "input"},
            )
        ),
    ],
)
def test_invalid_references(capability_api, policy):
    data = descriptor()
    data["actions"]["set_power"]["completion_policy"] = policy
    reject(capability_api, lambda: capability_api.validate_capability(data))


@pytest.mark.parametrize("change", ["read_only", "optional", "wrong_type", "bound", "enum_order"])
def test_incompatible_targets(capability_api, change):
    data = descriptor()
    prop = data["properties"]["power"]
    action = data["actions"]["set_power"]
    if change == "read_only":
        prop["read_only"] = True
    elif change == "optional":
        action["input_schema"]["required"] = []
    elif change == "wrong_type":
        action["input_schema"]["properties"]["power"] = {"type": "integer"}
    elif change == "bound":
        prop["value_schema"] = {"type": "integer"}
        action["input_schema"]["properties"]["power"] = {"type": "integer", "minimum": 0}
    else:
        prop["value_schema"] = {"type": "boolean", "enum": [False, True]}
        action["input_schema"]["properties"]["power"] = {"type": "boolean", "enum": [True, False]}
    reject(capability_api, lambda: capability_api.validate_capability(data))


def test_schema_key_order_and_numeric_equality(capability_api):
    data = descriptor()
    schema = {"type": "number", "minimum": 0, "maximum": 1, "enum": [0, 1]}
    data["properties"]["power"]["value_schema"] = schema
    source = {"enum": [0.0, 1.0], "maximum": 1.0, "minimum": 0.0, "type": "number"}
    data["actions"]["set_power"]["input_schema"]["properties"]["power"] = source
    assert capability_api.validate_capability(data) == data
    bad = deepcopy(data)
    bad["actions"]["set_power"]["input_schema"]["properties"]["power"]["enum"] = [True, 1]
    reject(capability_api, lambda: capability_api.validate_capability(bad))


@pytest.mark.parametrize(
    "interaction,field",
    [
        ("properties", "value_schema"),
        ("properties", "read_only"),
        ("properties", "title"),
        ("events", "data_schema"),
        ("events", "description"),
    ],
)
def test_interaction_required(capability_api, interaction, field):
    data = descriptor()
    record = next(iter(data[interaction].values()))
    del record[field]
    reject(capability_api, lambda: capability_api.validate_capability(data))


@pytest.mark.parametrize(
    "schema",
    [
        {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        {"type": "array", "items": {"type": "null"}},
        {"type": "null"},
    ],
)
def test_property_scalar_only(capability_api, schema):
    data = descriptor()
    data["properties"]["power"]["value_schema"] = schema
    data["actions"]["set_power"]["completion_policy"] = {"kind": "ack_only"}
    reject(capability_api, lambda: capability_api.validate_capability(data))


@pytest.mark.parametrize("value", [None, 0, 1, "false", []])
def test_strict_read_only(capability_api, value):
    data = descriptor()
    data["properties"]["power"]["read_only"] = value
    reject(capability_api, lambda: capability_api.validate_capability(data))


def test_typed_nested_factories(capability_api):
    api = capability_api
    data = descriptor()
    assert (
        api.Property.from_dict(data["properties"]["power"]).to_dict() == data["properties"]["power"]
    )
    assert api.Event.from_dict(data["events"]["changed"]).to_dict() == data["events"]["changed"]
    assert (
        api.Action.from_dict(data["actions"]["set_power"]).to_dict() == data["actions"]["set_power"]
    )
    policy = data["actions"]["set_power"]["completion_policy"]
    assert api.CompletionPolicy.from_dict(policy).to_dict() == policy
    source = policy["targets"]["power"]
    assert api.TargetSource.from_dict(source).to_dict() == source
    assert api.Schema.from_dict({"type": "number", "minimum": -5, "maximum": -1}).validate(-3) == -3
