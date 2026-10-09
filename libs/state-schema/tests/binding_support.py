"""Fictional binding data and direct API assertions for REQ-014."""

import json
from copy import deepcopy
from importlib.util import find_spec

import pytest
from inventory_support import ROOT

REPLACEMENT = (
    ROOT / "docs/product/home-intelligence/examples/provider-binding-replacement.example.json"
)
BINDING_AVAILABLE = find_spec("state_schema.provider_binding") is not None
binding_required = pytest.mark.skipif(
    not BINDING_AVAILABLE,
    reason="REQ-014 binding runtime absent; acceptance pending",
)


def replacement():
    return json.loads(REPLACEMENT.read_text(encoding="utf-8"))


def binding(provider="ha", device="device-bedroom-light-01", instance="fixture-instance"):
    return {
        "home_id": "home-example",
        "device_id": device,
        "provider": provider,
        "provider_instance_id": instance,
        "mapping": {"entity_ids": ["light.fictional"]}
        if provider == "ha"
        else {"device_key": "fictional-light"},
    }


def collection(*records):
    return {"schema_version": 1, "bindings": list(records)}


def error_at(api, call, path, *, private=()):
    errors = []
    for _ in range(2):
        with pytest.raises(api.BindingError) as caught:
            call()
        err = caught.value
        assert err.path == path
        assert isinstance(err.path, tuple)
        assert err.message.strip()
        assert str(err).startswith("$")
        for marker in private:
            assert marker not in str(err)
            assert marker not in repr(err)
            assert marker not in err.message
        errors.append((err.path, err.message, str(err)))
    assert errors[0] == errors[1]


def mutated(record, path, value):
    result = deepcopy(record)
    target = result
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    return result
