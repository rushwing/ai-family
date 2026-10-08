"""TC-014-03: reference integrity and canonical/provider separation."""

from copy import deepcopy

import pytest
from binding_support import binding, binding_required, collection, error_at

pytestmark = binding_required


@pytest.mark.parametrize("provider", ["ha", "mock"])
def test_partial_and_empty(binding_api, inventory, provider):
    original = deepcopy(inventory)
    assert binding_api.validate_bindings(collection(), inventory=inventory) == collection()
    assert (
        len(
            binding_api.validate_bindings(collection(binding(provider)), inventory=inventory)[
                "bindings"
            ]
        )
        == 1
    )
    assert inventory == original


@pytest.mark.parametrize("kind", ["home", "floors", "areas", "labels", "area_groups", "missing"])
def test_device_reference(binding_api, inventory, kind):
    device = (
        "missing-device"
        if kind == "missing"
        else inventory["home"]["id"]
        if kind == "home"
        else inventory[kind][0]["id"]
    )
    error_at(
        binding_api,
        lambda: binding_api.validate_bindings(
            collection(binding(device=device)), inventory=inventory
        ),
        ("bindings", 0, "device_id"),
    )


def test_wrong_home(binding_api, inventory):
    data = binding()
    data["home_id"] = "another-home"
    error_at(
        binding_api,
        lambda: binding_api.validate_bindings(collection(data), inventory=inventory),
        ("bindings", 0, "home_id"),
    )


@pytest.mark.parametrize(
    "kind", ["home", "floors", "areas", "devices", "labels", "area_groups", "root"]
)
def test_no_provider_fields_in_inventory(api, binding_api, inventory, kind):
    data = deepcopy(inventory)
    path = () if kind == "root" else ("home",) if kind == "home" else (kind, 0)
    target = data
    for part in path:
        target = target[part]
    target["provider"] = "ha"
    with pytest.raises(api.InventoryError) as caught:
        api.validate_inventory(data)
    assert caught.value.path == (*path, "provider")
    error_at(
        binding_api,
        lambda: binding_api.validate_bindings(collection(), inventory=data),
        ("inventory", *path, "provider"),
    )


def test_invalid_inventory_is_checked_even_for_empty_collection(binding_api, inventory):
    data = deepcopy(inventory)
    data["devices"][0]["home_id"] = "another-home"
    error_at(
        binding_api,
        lambda: binding_api.validate_bindings(collection(), inventory=data),
        ("inventory", "devices", 0, "home_id"),
    )
    data = deepcopy(inventory)
    data["devices"][0]["labels"] = ["private-label-marker"]
    error_at(
        binding_api,
        lambda: binding_api.validate_bindings(collection(), inventory=data),
        ("inventory", "devices", 0, "labels", 0),
        private=("private-label-marker",),
    )
