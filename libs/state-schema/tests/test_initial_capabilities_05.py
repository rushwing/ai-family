"""TC-017-05: actual catalogue validation and actual State evidence."""

from copy import deepcopy

import pytest
from capability_support import reject
from initial_capabilities_support import ACTIONS, CONTRACTS, initial_required
from state_support import availability, intent, observation, state

pytestmark = initial_required


@pytest.mark.parametrize("identity,action,member,schema,timeout,value", ACTIONS)
def test_ack_unknown_pending_then_observed(
    initial_api, state_api, identity, action, member, schema, timeout, value
):
    cat = initial_api.load_initial_capabilities()
    current = state()
    current["desired_state"] = intent({member: value})
    current["reported_state"] = {}
    before = deepcopy(current)
    assert cat.validate_payload(identity, 1, "action_input", action, {member: value}) == {
        member: value
    }
    assert cat.validate_payload(identity, 1, "action_output", action, None) is None
    assert (
        current == before and state_api.evaluate_convergence(current, current_epoch=1) == "unknown"
    )
    with pytest.raises(state_api.StateError):
        state_api.apply_state_update(current, current_epoch=1, availability={"accepted": True})
    mismatch = True if member == "is_on" else 49
    cat.validate_payload(identity, 1, "property", member, mismatch)
    pending = state_api.apply_state_update(
        current, current_epoch=1, reported_state={member: observation(mismatch, 2)}
    )
    pending_before = deepcopy(pending)
    assert state_api.evaluate_convergence(pending, current_epoch=1) == "pending"
    cat.validate_payload(identity, 1, "action_output", action, None)
    assert (
        pending == pending_before
        and state_api.evaluate_convergence(pending, current_epoch=1) == "pending"
    )
    cat.validate_payload(identity, 1, "property", member, value)
    confirmed = state_api.apply_state_update(
        pending, current_epoch=1, reported_state={member: observation(value, 3)}
    )
    assert state_api.evaluate_convergence(confirmed, current_epoch=1) == "confirmed"
    assert current == before


@pytest.mark.parametrize("identity,action,member,schema,timeout,value", ACTIONS)
@pytest.mark.parametrize(
    "fault",
    [
        "offline",
        "unknown",
        "old_epoch",
        "old_baseline",
        "null_baseline",
        "unknown_report",
        "missing",
        "mismatch",
    ],
)
def test_insufficient_evidence(
    initial_api, state_api, identity, action, member, schema, timeout, value, fault
):
    cat = initial_api.load_initial_capabilities()
    cat.validate_payload(identity, 1, "action_output", action, None)
    current = state()
    current["desired_state"] = intent({member: value})
    current["reported_state"] = {member: observation(value, 2)}
    expected = "unknown"
    if fault in ("offline", "unknown"):
        current["availability"] = availability(fault)
    elif fault == "old_epoch":
        current["reported_state"][member] = observation(value, 2, epoch=0)
    elif fault == "old_baseline":
        current["reported_state"][member] = observation(value, 1)
    elif fault == "null_baseline":
        current["desired_state"]["report_baseline"] = None
    elif fault == "unknown_report":
        current["reported_state"][member] = {
            "status": "unknown",
            "value": None,
            "observed_at": None,
            "ordering": None,
        }
    elif fault == "missing":
        current["reported_state"] = {}
    else:
        current["reported_state"][member] = observation(True if member == "is_on" else 49, 2)
        expected = "pending"
    assert state_api.evaluate_convergence(current, current_epoch=1) == expected


def test_float_position_requires_capability_validation(initial_api, capability_api, state_api):
    # Generic State scalars allow numeric agreement; Capability is the integer boundary.
    current = state()
    current["desired_state"] = intent({"position_percent": 50})
    current["reported_state"] = {}
    before = deepcopy(current)
    reject(
        capability_api,
        lambda: initial_api.load_initial_capabilities().validate_payload(
            "home.positionable", 1, "property", "position_percent", 50.0
        ),
    )
    assert (
        current == before and state_api.evaluate_convergence(current, current_epoch=1) == "unknown"
    )


@pytest.mark.parametrize("identity,title,member,schema,read_only", CONTRACTS[2:])
def test_sensor_zero_is_known_not_unknown(
    initial_api, state_api, identity, title, member, schema, read_only
):
    value = initial_api.load_initial_capabilities().validate_payload(
        identity, 1, "property", member, 0
    )
    current = state()
    current["desired_state"] = None
    current["reported_state"] = {}
    observed = state_api.apply_state_update(
        current, current_epoch=1, reported_state={member: observation(value, 3)}
    )
    assert member not in current["reported_state"]
    assert observed["reported_state"][member]["status"] == "known"
    assert observed["reported_state"][member]["value"] == 0
