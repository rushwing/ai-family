"""TC-014-04: per-device uniqueness and resource namespaces."""

import pytest
from binding_support import binding, binding_required, collection, error_at

pytestmark = binding_required


@pytest.mark.parametrize("provider", ["ha", "mock"])
@pytest.mark.parametrize("instance", ["fixture-instance", "other-instance"])
def test_duplicate_device(binding_api, inventory, provider, instance):
    data = collection(binding(), binding(provider, instance=instance))
    error_at(
        binding_api,
        lambda: binding_api.validate_bindings(data, inventory=inventory),
        ("bindings", 1, "device_id"),
    )


@pytest.mark.parametrize("provider", ["ha", "mock"])
def test_resource_collision(binding_api, inventory, provider):
    first = binding(provider)
    second = binding(provider, device="device-bedroom-light-02")
    expected = (
        ("bindings", 1, "mapping", "entity_ids", 0)
        if provider == "ha"
        else ("bindings", 1, "mapping", "device_key")
    )
    private = "fictional-sensitive-resource"
    for item in (first, second):
        item["mapping"] = {"entity_ids": [private]} if provider == "ha" else {"device_key": private}
    error_at(
        binding_api,
        lambda: binding_api.validate_bindings(collection(first, second), inventory=inventory),
        expected,
        private=(private,),
    )


def test_multi_entity_overlap(binding_api, inventory):
    first, second = binding(), binding(device="device-bedroom-light-02")
    first["mapping"]["entity_ids"] = ["light.first", "sensor.shared"]
    second["mapping"]["entity_ids"] = ["light.second", "sensor.shared"]
    error_at(
        binding_api,
        lambda: binding_api.validate_bindings(collection(first, second), inventory=inventory),
        ("bindings", 1, "mapping", "entity_ids", 1),
    )


@pytest.mark.parametrize("provider", ["ha", "mock"])
def test_distinct_instances(binding_api, inventory, provider):
    data = collection(
        binding(provider),
        binding(provider, device="device-bedroom-light-02", instance="another-instance"),
    )
    assert len(binding_api.validate_bindings(data, inventory=inventory)["bindings"]) == 2


def test_registry_id_is_not_unique_resource(binding_api, inventory):
    first, second = binding(), binding(device="device-bedroom-light-02")
    first["mapping"] = {"entity_ids": ["light.first"], "device_registry_id": "shared-registry"}
    second["mapping"] = {"entity_ids": ["light.second"], "device_registry_id": "shared-registry"}
    assert binding_api.validate_bindings(
        collection(first, second), inventory=inventory
    ) == collection(first, second)


def test_provider_namespaces_are_distinct(binding_api, inventory):
    first = binding()
    second = binding("mock", device="device-bedroom-light-02")
    second["mapping"]["device_key"] = first["mapping"]["entity_ids"][0]
    assert (
        len(
            binding_api.validate_bindings(collection(first, second), inventory=inventory)[
                "bindings"
            ]
        )
        == 2
    )
