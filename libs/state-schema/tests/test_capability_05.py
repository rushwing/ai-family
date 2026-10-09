"""TC-016-05: accepted output never changes actual State evidence."""

from copy import deepcopy

import pytest
from capability_support import capability_required, descriptor, reject
from state_support import availability, observation, state

pytestmark = capability_required


@pytest.mark.parametrize("kind", ["ack_only", "event_confirmed", "state_converged"])
def test_ack_and_observation_timeline(capability_api, state_api, kind):
    data = descriptor()
    if kind == "ack_only":
        data["actions"]["set_power"]["completion_policy"] = {"kind": kind}
    elif kind == "event_confirmed":
        data["actions"]["set_power"]["completion_policy"] = {"kind": kind, "event": "changed"}
    parsed = capability_api.CapabilityDescriptor.from_dict(data)
    before = state()
    before["reported_state"] = {}
    original = deepcopy(before)
    assert parsed.validate_payload("action_input", "set_power", {"power": False}) == {
        "power": False
    }
    assert parsed.validate_payload("action_output", "set_power", {"accepted": True}) == {
        "accepted": True
    }
    assert (
        before == original and state_api.evaluate_convergence(before, current_epoch=1) == "unknown"
    )
    with pytest.raises(state_api.StateError):
        state_api.apply_state_update(before, current_epoch=1, availability={"accepted": True})
    mismatch = state_api.apply_state_update(
        before, current_epoch=1, reported_state={"power": observation(True, 2)}
    )
    assert state_api.evaluate_convergence(mismatch, current_epoch=1) == "pending"
    matching = state_api.apply_state_update(
        mismatch, current_epoch=1, reported_state={"power": observation(False, 3)}
    )
    assert state_api.evaluate_convergence(matching, current_epoch=1) == "confirmed"
    assert before == original


@pytest.mark.parametrize("invalid", ["offline", "unknown", "old_epoch", "old_baseline"])
def test_insufficient_physical_evidence(capability_api, state_api, invalid):
    parsed = capability_api.CapabilityDescriptor.from_dict(descriptor())
    assert parsed.validate_payload("action_output", "set_power", {"accepted": True})
    data = state()
    if invalid in ("offline", "unknown"):
        data["availability"] = availability(invalid)
    elif invalid == "old_epoch":
        data["reported_state"]["power"] = observation(False, 2, epoch=0)
    else:
        data["reported_state"]["power"] = observation(False, 1)
    assert state_api.evaluate_convergence(data, current_epoch=1) == "unknown"


@pytest.mark.parametrize(
    "field", ["ack", "success", "converged", "provider_id", "entity_id", "dispatch"]
)
def test_no_runtime_descriptor_fields(capability_api, field):
    data = descriptor()
    data[field] = True
    reject(capability_api, lambda: capability_api.validate_capability(data), ("<unknown>",))


def test_event_shape_is_not_task_correlation(capability_api):
    data = descriptor()
    data["actions"]["set_power"]["completion_policy"] = {
        "kind": "event_confirmed",
        "event": "changed",
    }
    parsed = capability_api.CapabilityDescriptor.from_dict(data)
    # A payload may be schema-valid without any request/event correlation.
    # There is deliberately no completion-policy evaluator to certify a task.
    assert parsed.validate_payload("event", "changed", {"power": False}) == {"power": False}
    assert not hasattr(parsed, "evaluate_completion")
    assert not hasattr(parsed, "dispatch")


@pytest.mark.parametrize("value", [False, 0, 0.0])
def test_ack_does_not_finish_pending_intent(capability_api, state_api, value):
    data = descriptor()
    schema = {"type": "boolean"} if type(value) is bool else {"type": "number"}
    data["properties"]["power"]["value_schema"] = schema
    data["actions"]["set_power"]["input_schema"]["properties"]["power"] = schema
    parsed = capability_api.CapabilityDescriptor.from_dict(data)
    current = state()
    current["desired_state"]["values"] = {"power": value}
    current["reported_state"]["power"] = observation(True, 2)
    assert state_api.evaluate_convergence(current, current_epoch=1) == "pending"
    snapshot = deepcopy(current)
    assert parsed.validate_payload("action_output", "set_power", {"accepted": True})
    assert (
        current == snapshot
        and state_api.evaluate_convergence(current, current_epoch=1) == "pending"
    )
    updated = state_api.apply_state_update(
        current, current_epoch=1, reported_state={"power": observation(value, 3)}
    )
    assert state_api.evaluate_convergence(updated, current_epoch=1) == "confirmed"
    updated["desired_state"]["report_baseline"] = None
    assert state_api.evaluate_convergence(updated, current_epoch=1) == "unknown"
