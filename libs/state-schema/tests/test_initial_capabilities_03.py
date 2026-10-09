"""TC-017-03: action contracts and forbidden sensor actions/events."""

from copy import deepcopy

import pytest
from capability_support import obj, reject
from initial_capabilities_support import ACTIONS, CONTRACTS, initial_required

pytestmark = initial_required


@pytest.mark.parametrize("identity,action,member,schema,timeout,value", ACTIONS)
def test_exact_action_metadata(initial_api, identity, action, member, schema, timeout, value):
    raw = initial_api.load_initial_capabilities().get(identity, 1).to_dict()
    assert list(raw["actions"]) == [action]
    definition = raw["actions"][action]
    assert definition["input_schema"] == obj({member: schema})
    assert definition["output_schema"] == {"type": "null"}
    assert (definition["risk"], definition["timeout_ms"], definition["idempotency"]) == (
        "medium",
        timeout,
        "safe_repeat",
    )
    assert definition["completion_policy"] == {
        "kind": "state_converged",
        "targets": {member: {"source": "input", "field": member}},
    }
    assert (
        definition["input_schema"]["properties"][member]
        == raw["properties"][member]["value_schema"]
    )


@pytest.mark.parametrize(
    "identity,action,member,value",
    [
        ("home.switchable", "set_on", "is_on", True),
        ("home.switchable", "set_on", "is_on", False),
        ("home.positionable", "set_position", "position_percent", 0),
        ("home.positionable", "set_position", "position_percent", 50),
        ("home.positionable", "set_position", "position_percent", 100),
    ],
)
def test_valid_input_and_null_output(initial_api, identity, action, member, value):
    cat = initial_api.load_initial_capabilities()
    payload = {member: value}
    assert cat.validate_payload(identity, 1, "action_input", action, payload) == payload
    assert cat.validate_payload(identity, 1, "action_output", action, None) is None


@pytest.mark.parametrize("identity,action,member,schema,timeout,value", ACTIONS)
@pytest.mark.parametrize("invalid", ["missing", "extra", "wrong", "null", "string", "float"])
def test_invalid_inputs(
    initial_api, capability_api, identity, action, member, schema, timeout, value, invalid
):
    payload = {member: value}
    if invalid == "missing":
        payload = {}
    elif invalid == "extra":
        payload["PRIVATE_ARGUMENT"] = "PRIVATE_PAYLOAD"
    else:
        payload[member] = {
            "wrong": 1 if identity == "home.switchable" else True,
            "null": None,
            "string": "50",
            "float": 50.0,
        }[invalid]
    before = deepcopy(payload)
    reject(
        capability_api,
        lambda: initial_api.load_initial_capabilities().validate_payload(
            identity, 1, "action_input", action, payload
        ),
        private=("PRIVATE_ARGUMENT", "PRIVATE_PAYLOAD"),
    )
    assert payload == before


@pytest.mark.parametrize("identity,action,member,schema,timeout,value", ACTIONS)
@pytest.mark.parametrize("payload", [{"accepted": True}, True, {}])
def test_ack_is_not_output(
    initial_api, capability_api, identity, action, member, schema, timeout, value, payload
):
    reject(
        capability_api,
        lambda: initial_api.load_initial_capabilities().validate_payload(
            identity, 1, "action_output", action, payload
        ),
    )


@pytest.mark.parametrize("identity,title,member,schema,read_only", CONTRACTS[2:])
def test_sensor_has_no_write_surface(
    initial_api, capability_api, identity, title, member, schema, read_only
):
    cat = initial_api.load_initial_capabilities()
    raw = cat.get(identity, 1).to_dict()
    assert raw["actions"] == raw["events"] == {} and raw["properties"][member]["read_only"] is True
    for action in ("set_on", "reset", "calibrate", "set_position"):
        for kind in ("action_input", "action_output"):
            reject(
                capability_api,
                lambda: cat.validate_payload(identity, 1, kind, action, {}),
                ("<unknown>",),
            )


@pytest.mark.parametrize("identity,title,member,schema,read_only", CONTRACTS)
def test_no_events(initial_api, capability_api, identity, title, member, schema, read_only):
    reject(
        capability_api,
        lambda: initial_api.load_initial_capabilities().validate_payload(
            identity, 1, "event", "changed", {}
        ),
        ("<unknown>",),
    )
