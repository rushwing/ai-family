"""TC-015-04: owner-established generations and separate intent revision."""

from copy import deepcopy

import pytest
from state_support import availability, error_at, intent, observation, order, state, state_required

pytestmark = state_required


@pytest.mark.parametrize("branch", ["report", "availability"])
@pytest.mark.parametrize("epoch", [0, 2])
def test_unestablished_epochs_reject(state_api, branch, epoch):
    kwargs = {"reported_state": {"power": observation(True, 999999, epoch)}}
    path = ("reported_state", "power", "ordering", "epoch")
    if branch == "availability":
        kwargs = {"availability": availability("offline", 999999, epoch)}
        path = ("availability", "ordering", "epoch")
    error_at(
        state_api, lambda: state_api.apply_state_update(state(), current_epoch=1, **kwargs), path
    )


@pytest.mark.parametrize("epoch", [True, -1, 1.0, None, "1", 0])
@pytest.mark.parametrize("helper", ["apply_state_update", "evaluate_convergence"])
def test_epoch_context(state_api, epoch, helper):
    error_at(
        state_api,
        lambda: getattr(state_api, helper)(state(), current_epoch=epoch),
        ("current_epoch",),
    )


def test_restart_refresh_and_intent_rebase(state_api):
    data = state()
    assert state_api.evaluate_convergence(data, current_epoch=2) == "unknown"
    assert state_api.apply_state_update(data, current_epoch=2) == data
    result = state_api.apply_state_update(
        data,
        current_epoch=2,
        reported_state={"power": observation(False, 0, 2)},
        availability=availability("online", 0, 2),
    )
    assert result["reported_state"]["power"]["ordering"] == order(0, 2)
    assert state_api.evaluate_convergence(result, current_epoch=2) == "unknown"
    error_at(
        state_api,
        lambda: state_api.apply_state_update(
            result, current_epoch=2, reported_state={"power": observation(True, 999999, 1)}
        ),
        ("reported_state", "power", "ordering", "epoch"),
    )
    rebased = intent(revision=2, baseline=order(0, 2))
    result = state_api.apply_state_update(result, current_epoch=2, desired_state=rebased)
    assert state_api.evaluate_convergence(result, current_epoch=2) == "unknown"
    result = state_api.apply_state_update(
        result, current_epoch=2, reported_state={"power": observation(False, 1, 2)}
    )
    assert state_api.evaluate_convergence(result, current_epoch=2) == "confirmed"
    error_at(
        state_api,
        lambda: state_api.evaluate_convergence(result, current_epoch=1),
        ("current_epoch",),
    )


@pytest.mark.parametrize("revision", [1, 2, 3])
def test_desired_revision(state_api, revision):
    data = state()
    data["desired_state"]["revision"] = 2
    original = deepcopy(data)
    candidate = intent({"power": True}, revision)
    if revision == 2:
        error_at(
            state_api,
            lambda: state_api.apply_state_update(data, current_epoch=1, desired_state=candidate),
            ("desired_state", "revision"),
        )
    else:
        result = state_api.apply_state_update(data, current_epoch=1, desired_state=candidate)
        assert result["desired_state"] == (data["desired_state"] if revision < 2 else candidate)
        assert result["reported_state"] == data["reported_state"]
    assert data == original
    assert (
        state_api.apply_state_update(data, current_epoch=1, desired_state=data["desired_state"])
        == data
    )


def test_intent_typed_conflict_and_initial_intent(state_api):
    error_at(
        state_api,
        lambda: state_api.apply_state_update(
            state(), current_epoch=1, desired_state=intent({"power": 0})
        ),
        ("desired_state", "revision"),
    )
    data = state()
    data["desired_state"] = None
    assert (
        state_api.apply_state_update(data, current_epoch=1, desired_state=intent())["desired_state"]
        == intent()
    )


def test_future_intent_baseline_and_clock_independence(state_api):
    error_at(
        state_api,
        lambda: state_api.apply_state_update(
            state(), current_epoch=1, desired_state=intent(revision=2, baseline=order(0, 2))
        ),
        ("desired_state", "report_baseline", "epoch"),
    )
    data = state()
    data["reported_state"]["power"]["observed_at"] = "2000-01-01T00:00:00Z"
    assert state_api.evaluate_convergence(data, current_epoch=1) == "confirmed"


def test_desired_map_order_is_not_a_revision_conflict(state_api):
    data = state()
    data["desired_state"]["values"] = {"power": False, "level": 0}
    candidate = intent({"level": 0, "power": False})
    assert state_api.apply_state_update(data, current_epoch=1, desired_state=candidate) == data
