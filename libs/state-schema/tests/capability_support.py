"""Fictional Capability fixtures and direct REQ-016 public-boundary checks."""

from copy import deepcopy
from importlib.util import find_spec

import pytest

capability_required = pytest.mark.skipif(
    find_spec("state_schema.capability") is None,
    reason="REQ-016 Capability runtime absent; acceptance pending",
)


def obj(properties=None, required=None):
    properties = {} if properties is None else properties
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties) if required is None else required,
        "additionalProperties": False,
    }


def descriptor():
    return {
        "schema_version": 1,
        "capability_id": "demo.power",
        "capability_version": 1,
        "title": "Fictional power",
        "description": "Offline review fixture.",
        "properties": {
            "power": {
                "title": "Power",
                "description": "Observed power.",
                "value_schema": {"type": "boolean"},
                "read_only": False,
            }
        },
        "actions": {
            "set_power": {
                "title": "Set power",
                "description": "Declare an intent.",
                "input_schema": obj({"power": {"type": "boolean"}}),
                "output_schema": obj({"accepted": {"type": "boolean"}}),
                "risk": "low",
                "timeout_ms": 5000,
                "idempotency": "key_required",
                "completion_policy": {
                    "kind": "state_converged",
                    "targets": {"power": {"source": "input", "field": "power"}},
                },
            }
        },
        "events": {
            "changed": {
                "title": "Changed",
                "description": "Fictional event.",
                "data_schema": obj({"power": {"type": "boolean"}}),
            }
        },
    }


def catalogue(*values):
    return {"schema_version": 1, "capabilities": list(values)}


def changed(data, path, value):
    data = deepcopy(data)
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return data


def reject(api, call, path=None, private=()):
    recorded = []
    for _ in range(2):
        with pytest.raises(api.CapabilityError) as caught:
            call()
        error = caught.value
        assert isinstance(error.path, tuple) and error.message
        if path is not None:
            assert error.path == path
        for value in private:
            assert value not in str(error) and value not in repr(error)
        assert error.__suppress_context__ or error.__context__ is None
        recorded.append((error.path, error.message))
    assert recorded[0] == recorded[1]
