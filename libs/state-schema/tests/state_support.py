"""Fictional data and direct public API assertions for REQ-015."""

from copy import deepcopy
from importlib.util import find_spec

import pytest

STATE_AVAILABLE = find_spec("state_schema.canonical_state") is not None
state_required = pytest.mark.skipif(
    not STATE_AVAILABLE,
    reason="REQ-015 State runtime absent; acceptance pending",
)
TIME = "2026-01-01T12:00:00Z"


def order(sequence=2, epoch=1):
    return {"epoch": epoch, "sequence": sequence}


def observation(value=False, sequence=2, epoch=1, time=TIME):
    return {
        "status": "known",
        "value": value,
        "observed_at": time,
        "ordering": order(sequence, epoch),
    }


def availability(status="online", sequence=2, epoch=1):
    return {"status": status, "observed_at": TIME, "ordering": order(sequence, epoch)}


def intent(values=None, revision=1, baseline=None):
    return {
        "revision": revision,
        "values": {"power": False} if values is None else values,
        "report_baseline": order(1) if baseline is None else baseline,
    }


def state():
    return {
        "home_id": "home-example",
        "device_id": "device-bedroom-light-01",
        "desired_state": intent(),
        "reported_state": {"power": observation()},
        "availability": availability(),
    }


def collection(*records):
    return {"schema_version": 1, "states": list(records)}


def changed(data, path, value):
    result = deepcopy(data)
    target = result
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return result


def error_at(api, call, path, private=()):
    errors = []
    for _ in range(2):
        with pytest.raises(api.StateError) as caught:
            call()
        err = caught.value
        assert err.path == path
        assert isinstance(err.path, tuple)
        assert err.message.strip()
        for marker in private:
            assert marker not in str(err)
            assert marker not in repr(err)
            assert marker not in err.message
        errors.append((err.path, err.message, str(err)))
    assert errors[0] == errors[1]
