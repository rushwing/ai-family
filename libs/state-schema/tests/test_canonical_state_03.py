"""TC-015-03: member ordering, exact replay, partial batches and isolation."""

from copy import deepcopy

import pytest
from state_support import availability, error_at, observation, order, state, state_required

pytestmark = state_required


@pytest.mark.parametrize("branch", ["report", "availability"])
@pytest.mark.parametrize("sequence", [0, 1, 2, 3, 100])
def test_ordering_vs_time(state_api, branch, sequence):
    data = state()
    original = deepcopy(data)
    candidate = observation(True, sequence, time="2000-01-01T00:00:00Z")
    if branch == "availability":
        candidate = availability("offline", sequence)
        candidate["observed_at"] = "2000-01-01T00:00:00Z"
    kwargs = (
        {"reported_state": {"power": candidate}}
        if branch == "report"
        else {"availability": candidate}
    )
    if sequence == 2:
        path = (
            ("reported_state", "power", "ordering")
            if branch == "report"
            else ("availability", "ordering")
        )
        error_at(
            state_api, lambda: state_api.apply_state_update(data, current_epoch=1, **kwargs), path
        )
    else:
        result = state_api.apply_state_update(data, current_epoch=1, **kwargs)
        if sequence < 2:
            assert result == data
        else:
            assert (
                result["reported_state"]["power"] if branch == "report" else result["availability"]
            ) == candidate
    assert data == original


def test_replay_is_exact_and_detached(state_api):
    data = state()
    result = state_api.apply_state_update(
        data,
        current_epoch=1,
        reported_state=data["reported_state"],
        availability=data["availability"],
    )
    assert result == data
    result["reported_state"]["power"]["value"] = True
    assert data["reported_state"]["power"]["value"] is False


@pytest.mark.parametrize("field,value", [("value", 0), ("observed_at", "2000-01-01T00:00:00Z")])
def test_typed_replay_conflict(state_api, field, value):
    candidate = observation()
    candidate[field] = value
    error_at(
        state_api,
        lambda: state_api.apply_state_update(
            state(), current_epoch=1, reported_state={"power": candidate}
        ),
        ("reported_state", "power", "ordering"),
    )


def test_partial_members_and_explicit_unknown(state_api):
    data = state()
    data["reported_state"]["temperature"] = observation(20, 100)
    result = state_api.apply_state_update(
        data, current_epoch=1, reported_state={"power": observation(True, 3)}
    )
    assert result["reported_state"]["temperature"] == data["reported_state"]["temperature"]
    assert result["availability"] == data["availability"]
    unknown = {
        "status": "unknown",
        "value": None,
        "observed_at": observation()["observed_at"],
        "ordering": order(4),
    }
    result = state_api.apply_state_update(
        result, current_epoch=1, reported_state={"power": unknown}
    )
    assert result["reported_state"]["power"] == unknown
    assert (
        state_api.apply_state_update(
            result, current_epoch=1, reported_state={"power": observation(False, 3)}
        )
        == result
    )
    assert state_api.apply_state_update(result, current_epoch=1, reported_state={}) == result


def test_failed_batch_is_atomic(state_api):
    data = state()
    original = deepcopy(data)
    error_at(
        state_api,
        lambda: state_api.apply_state_update(
            data,
            current_epoch=1,
            reported_state={"temperature": observation(20, 3), "power": observation(True, 2)},
        ),
        ("reported_state", "power", "ordering"),
    )
    assert data == original
    error_at(
        state_api,
        lambda: state_api.apply_state_update(
            data,
            current_epoch=1,
            reported_state={"power": observation(True, 3)},
            availability=availability("offline", 2),
        ),
        ("availability", "ordering"),
    )
    assert data == original


@pytest.mark.parametrize("branch", ["report", "availability"])
def test_unobserved_snapshot_is_not_an_update_event(state_api, branch):
    candidate = {"status": "unknown", "observed_at": None, "ordering": None}
    kwargs = {"availability": candidate}
    path = ("availability", "ordering")
    if branch == "report":
        candidate["value"] = None
        kwargs = {"reported_state": {"power": candidate}}
        path = ("reported_state", "power", "ordering")
    error_at(
        state_api, lambda: state_api.apply_state_update(state(), current_epoch=1, **kwargs), path
    )


def test_numeric_replay_retains_exact_type(state_api):
    data = state()
    data["reported_state"]["power"] = observation(0)
    error_at(
        state_api,
        lambda: state_api.apply_state_update(
            data, current_epoch=1, reported_state={"power": observation(0.0)}
        ),
        ("reported_state", "power", "ordering"),
    )
    candidate = {
        "status": "unknown",
        "value": None,
        "observed_at": observation()["observed_at"],
        "ordering": order(2),
    }
    error_at(
        state_api,
        lambda: state_api.apply_state_update(
            data, current_epoch=1, reported_state={"power": candidate}
        ),
        ("reported_state", "power", "ordering"),
    )


def test_new_property_and_previously_unobserved_availability(state_api):
    data = state()
    data["availability"] = {"status": "unknown", "observed_at": None, "ordering": None}
    result = state_api.apply_state_update(
        data,
        current_epoch=1,
        reported_state={"temperature": observation(20, 0)},
        availability=availability("online", 0),
    )
    assert result["reported_state"]["temperature"] == observation(20, 0)
    assert result["reported_state"]["power"] == data["reported_state"]["power"]
    assert result["availability"] == availability("online", 0)
