"""TC-015-05: eligible observations, value agreement and ACK boundary."""

import json
from copy import deepcopy

import pytest
from inventory_support import ROOT
from state_support import error_at, intent, observation, order, state, state_required

pytestmark = state_required


@pytest.mark.parametrize(
    "case",
    [
        "no_intent",
        "null_baseline",
        "old_baseline",
        "absent",
        "before",
        "at_baseline",
        "old_report",
        "old_availability",
        "offline",
        "unknown_availability",
        "unknown_report",
        "mismatch",
    ],
)
def test_convergence_prerequisites(state_api, case):
    data = state()
    if case == "no_intent":
        data["desired_state"] = None
    elif case == "null_baseline":
        data["desired_state"]["report_baseline"] = None
    elif case == "old_baseline":
        data["desired_state"]["report_baseline"] = order(1, 0)
    elif case == "absent":
        data["reported_state"] = {}
    elif case in ("before", "at_baseline"):
        data["reported_state"]["power"]["ordering"] = order(0 if case == "before" else 1)
    elif case == "old_report":
        data["reported_state"]["power"]["ordering"] = order(999, 0)
    elif case == "old_availability":
        data["availability"]["ordering"] = order(999, 0)
    elif case == "offline":
        data["availability"]["status"] = "offline"
    elif case == "unknown_availability":
        data["availability"] = {"status": "unknown", "observed_at": None, "ordering": None}
    elif case == "unknown_report":
        data["reported_state"]["power"].update(status="unknown", value=None)
    else:
        data["reported_state"]["power"]["value"] = True
    expected = (
        "not_requested" if case == "no_intent" else "pending" if case == "mismatch" else "unknown"
    )
    assert state_api.evaluate_convergence(data, current_epoch=1) == expected


@pytest.mark.parametrize(
    "desired,reported,expected",
    [
        (False, 0, "pending"),
        (0, False, "pending"),
        (True, 1, "pending"),
        (0, 0.0, "confirmed"),
        (0.0, 0, "confirmed"),
        (False, False, "confirmed"),
        ("", "", "confirmed"),
        ("0", 0, "pending"),
        ("unknown", "unknown", "confirmed"),
    ],
)
def test_type_sensitive_matching(state_api, desired, reported, expected):
    data = state()
    data["desired_state"] = intent({"power": desired})
    data["reported_state"]["power"] = observation(reported)
    data["reported_state"]["extra"] = observation("ignored", 0, 0)
    assert state_api.evaluate_convergence(data, current_epoch=1) == expected


def test_ineligible_member_dominates_mismatch(state_api):
    data = state()
    data["desired_state"]["values"] = {"power": True, "level": 0}
    assert state_api.evaluate_convergence(data, current_epoch=1) == "unknown"
    data["reported_state"]["level"] = observation(0)
    assert state_api.evaluate_convergence(data, current_epoch=1) == "pending"
    data["reported_state"]["power"] = observation(True)
    assert state_api.evaluate_convergence(data, current_epoch=1) == "confirmed"


@pytest.mark.parametrize("field", ["ack", "success", "converged"])
@pytest.mark.parametrize("branch", ["root", "report", "availability", "desired"])
def test_forged_ack_fields_reject(state_api, field, branch):
    data = state()
    obj = {
        "root": data,
        "report": data["reported_state"]["power"],
        "availability": data["availability"],
        "desired": data["desired_state"],
    }[branch]
    obj[field] = True
    path = {
        "root": (),
        "report": ("reported_state", "power"),
        "availability": ("availability",),
        "desired": ("desired_state",),
    }[branch]
    error_at(state_api, lambda: state_api.validate_state(data), (*path, "<unknown>"))


def test_public_ack_timeline(state_api, inventory):
    fixture = json.loads(
        (
            ROOT / "docs/product/home-intelligence/examples/canonical-state-timeline.example.json"
        ).read_text()
    )
    data = fixture["initial_state"]
    original = deepcopy(data)
    assert state_api.validate_states({"schema_version": 1, "states": [data]}, inventory=inventory)
    assert state_api.evaluate_convergence(data, current_epoch=1) == "unknown"
    assert fixture["provider_ack"] == {"accepted": True}
    # ACK is task evidence outside State; it has no update argument or dispatch path.
    assert state_api.apply_state_update(data, current_epoch=1) == original
    assert state_api.evaluate_convergence(data, current_epoch=1) == "unknown"
    for event, expected in zip(fixture["observations"], ["pending", "confirmed"], strict=True):
        data = state_api.apply_state_update(data, current_epoch=1, **event)
        assert state_api.evaluate_convergence(data, current_epoch=1) == expected
    assert original == fixture["initial_state"]
