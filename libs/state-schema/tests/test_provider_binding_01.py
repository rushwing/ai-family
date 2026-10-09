"""TC-014-01: typed/JSON round trips, optional normalization and isolation."""

import json
from dataclasses import FrozenInstanceError

import pytest
from binding_support import binding, binding_required, collection

pytestmark = binding_required


@pytest.mark.parametrize("provider", ["ha", "mock"])
@pytest.mark.parametrize("instance", ["a", "ha-main", "mock_fixture_01", "a" * 64])
def test_instance_alias_round_trip(binding_api, inventory, provider, instance):
    data = binding(provider, instance=instance)
    normalized = binding_api.validate_binding(data)
    assert normalized["provider_instance_id"] == instance
    assert binding_api.ProviderBinding.from_dict(data).to_dict() == normalized
    snapshot = binding_api.BindingCollection.from_dict(
        collection(data), inventory=inventory
    ).to_dict()
    assert snapshot == collection(normalized)
    assert binding_api.validate_bindings(snapshot, inventory=inventory) == snapshot


@pytest.mark.parametrize(
    "mapping",
    [
        {"entity_ids": ["light.fictional"]},
        {"entity_ids": ["opaque ID With Spaces", "sensor.fictional"], "device_registry_id": None},
        {"entity_ids": ["light.fictional"], "device_registry_id": "Registry ID With Spaces"},
        {"device_key": "Mock Key With Spaces"},
    ],
)
def test_round_trip(binding_api, inventory, mapping):
    data = binding("mock" if "device_key" in mapping else "ha")
    data["mapping"] = mapping
    normalized = binding_api.validate_binding(data)
    assert normalized == {
        **data,
        "mapping": (
            {"device_registry_id": None, **mapping} if data["provider"] == "ha" else mapping
        ),
    }
    model = binding_api.ProviderBinding.from_dict(data)
    assert model.to_dict() == normalized
    assert binding_api.validate_binding(json.loads(json.dumps(normalized))) == normalized
    group = binding_api.BindingCollection.from_dict(collection(data), inventory=inventory)
    assert group.to_dict() == collection(normalized)
    assert (
        binding_api.validate_bindings(json.loads(json.dumps(group.to_dict())), inventory=inventory)
        == group.to_dict()
    )


@pytest.mark.parametrize("provider", ["ha", "mock"])
def test_frozen_and_detached(binding_api, inventory, provider):
    data = binding(provider)
    group = binding_api.BindingCollection.from_dict(collection(data), inventory=inventory)
    original = group.to_dict()
    record = group.bindings[0]
    with pytest.raises(FrozenInstanceError):
        record.device_id = "changed"
    with pytest.raises(FrozenInstanceError):
        record.mapping = None
    with pytest.raises(FrozenInstanceError):
        group.bindings = ()
    with pytest.raises(FrozenInstanceError):
        if provider == "ha":
            record.mapping.device_registry_id = "changed"
        else:
            record.mapping.device_key = "changed"
    assert isinstance(group.bindings, tuple)
    if provider == "ha":
        assert isinstance(record.mapping.entity_ids, tuple)
        data["mapping"]["entity_ids"].append("sensor.changed")
    data["device_id"] = "changed"
    snapshot = group.to_dict()
    snapshot["bindings"][0]["mapping"].clear()
    snapshot["bindings"].clear()
    assert group.to_dict() == original


def test_shape_validation_is_not_reference_validation(binding_api, inventory):
    data = binding(device="unknown-device")
    assert binding_api.validate_binding(data)["device_id"] == "unknown-device"
    with pytest.raises(binding_api.BindingError):
        binding_api.validate_bindings(collection(data), inventory=inventory)
