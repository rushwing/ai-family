"""TC-015-02: unavailable is never an implicit off/zero value."""

import pytest
from state_support import availability, observation, state, state_required

pytestmark = state_required


@pytest.mark.parametrize("value", [False, 0, 0.0, "", "unknown"])
@pytest.mark.parametrize("status", ["online", "offline", "unknown"])
def test_known_values_and_availability(state_api, value, status):
    data = state()
    data["reported_state"]["power"] = observation(value)
    data["desired_state"]["values"]["power"] = value
    data["availability"] = availability(status)
    snapshot = state_api.validate_state(data)
    assert type(snapshot["reported_state"]["power"]["value"]) is type(value)
    assert snapshot["reported_state"]["power"]["value"] == value
    assert state_api.evaluate_convergence(data, current_epoch=1) == (
        "confirmed" if status == "online" else "unknown"
    )


@pytest.mark.parametrize("explicit", [False, True])
def test_unknown_report(state_api, explicit):
    data = state()
    data["reported_state"]["power"] = {
        "status": "unknown",
        "value": None,
        "observed_at": observation()["observed_at"] if explicit else None,
        "ordering": observation()["ordering"] if explicit else None,
    }
    assert state_api.validate_state(data) == data
    assert state_api.evaluate_convergence(data, current_epoch=1) == "unknown"
    data["reported_state"] = {}
    assert state_api.validate_state(data)["reported_state"] == {}
    assert state_api.evaluate_convergence(data, current_epoch=1) == "unknown"
