"""TC-014-05: fixture-only HA-to-mock replacement, with stable canonical identity."""

from copy import deepcopy

import pytest
from binding_support import binding_required, replacement

pytestmark = binding_required


def test_replacement(binding_api, api, inventory):
    fixture = replacement()
    untouched = deepcopy((inventory, fixture))
    before = binding_api.BindingCollection.from_dict(fixture["before"], inventory=inventory)
    canonical_before = api.Inventory.from_dict(inventory).to_dict()
    selectors = [{"area_ids": [area["id"]]} for area in inventory["areas"]]
    selectors += [{"area_group_ids": [group["id"]]} for group in inventory["area_groups"]]
    selectors += [{"area_group_ids": ["resting"], "label_ids": ["children"]}]
    targets = [
        api.resolve_targets(inventory, home_id="home-example", selector=s) for s in selectors
    ]
    after = binding_api.BindingCollection.from_dict(fixture["after"], inventory=inventory)
    old, new = before.to_dict()["bindings"], after.to_dict()["bindings"]
    assert old[0]["home_id"] == new[0]["home_id"] == "home-example"
    assert old[0]["device_id"] == new[0]["device_id"] == "device-bedroom-light-01"
    assert old[0]["provider"] == "ha"
    assert new[0]["provider"] == "mock"
    for field in ("provider_instance_id", "mapping"):
        assert old[0][field] != new[0][field]
    assert old[1:] == new[1:]
    assert api.Inventory.from_dict(inventory).to_dict() == canonical_before
    assert [
        api.resolve_targets(inventory, home_id="home-example", selector=s) for s in selectors
    ] == targets
    assert (inventory, fixture) == untouched


@pytest.mark.parametrize("fault", ["missing", "incomplete", "unknown_device"])
def test_failed_replacement_preserves_inputs(binding_api, inventory, fault):
    fixture = replacement()
    before = binding_api.BindingCollection.from_dict(fixture["before"], inventory=inventory)
    accepted = before.to_dict()
    original_inventory = deepcopy(inventory)
    invalid = deepcopy(fixture["after"])
    if fault == "missing":
        del invalid["bindings"][0]["mapping"]
    elif fault == "incomplete":
        invalid["bindings"][0]["mapping"] = {}
    else:
        invalid["bindings"][0]["device_id"] = "unknown-device"
    original_invalid = deepcopy(invalid)
    with pytest.raises(binding_api.BindingError):
        binding_api.validate_bindings(invalid, inventory=inventory)
    assert before.to_dict() == accepted
    assert inventory == original_inventory
    assert invalid == original_invalid
    assert fixture == replacement()
