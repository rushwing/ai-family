"""Isolated installed mapper smoke; explicit checks also execute under -O."""

import copy
import json


def check():
    from home_device_fabric.ha_mapping import HAMappingError, HARegistryMapper
    from state_schema.home_inventory import Inventory
    from state_schema.provider_binding import BindingCollection

    def require(condition):
        if not condition:
            raise RuntimeError("installed_mapping_check_failed")

    config = {
        "schema_version": 1,
        "home": {"id": "home-example", "name": "Example", "residence_type": "other"},
        "provider_instance_id": "ha-example",
        "area_ids": {"raw-room": "area-example"},
        "device_ids": {"raw-device": "device-example"},
        "entity_ids": {"sensor.solo": "device-solo"},
    }
    data = {
        "areas": [{"area_id": "raw-room", "name": "Example room"}],
        "devices": [{"id": "raw-device", "area_id": "raw-room"}],
        "entities": [
            {"entity_id": "switch.example", "device_id": "raw-device"},
            {"entity_id": "sensor.example", "device_id": "raw-device"},
            {"entity_id": "sensor.solo"},
        ],
        "states": [],
    }
    mapper = HARegistryMapper(config)
    result = mapper.map(data)
    projected = result.for_adapter()
    require([row["id"] for row in projected["inventory"]["devices"]]
            == ["device-example", "device-solo"])
    require(projected["bindings"]["bindings"][0]["mapping"] == {
        "entity_ids": ["sensor.example", "switch.example"], "device_registry_id": "raw-device"})
    require(projected["inventory"]["devices"][0]["area_id"] == "area-example")
    require(Inventory.from_dict(projected["inventory"]).to_dict() == projected["inventory"])
    require(BindingCollection.from_dict(projected["bindings"], inventory=projected["inventory"]
                                        ).to_dict() == projected["bindings"])
    changed = copy.deepcopy(data)
    changed["entities"].reverse()
    require(mapper.map(changed).for_adapter() == projected)
    changed["entities"] = []
    require(mapper.map(changed).for_adapter()["inventory"]["devices"] == [])
    config["device_ids"] = {}
    require(mapper.map(data).for_adapter() == projected)
    exported = result.for_adapter()
    exported["inventory"]["devices"].clear()
    require(result.for_adapter() == projected)
    changed = copy.deepcopy(data)
    changed["devices"][0]["disabled_by"] = "user"
    require([row["id"] for row in mapper.map(changed).for_adapter()["inventory"]["devices"]]
            == ["device-solo"])
    changed = copy.deepcopy(data)
    changed["areas"] = []
    require(mapper.map(changed).for_adapter()["inventory"]["devices"][0]["area_id"] is None)
    changed = copy.deepcopy(data)
    changed["entities"][0]["entity_id"] = "sensor.example"
    try:
        mapper.map(changed)
    except HAMappingError as error:
        require(error.code == "invalid_discovery" and error.__context__ is None)
    else:
        raise RuntimeError("installed_mapping_check_failed")
    require("raw-device" not in repr(mapper) + repr(result)
            + json.dumps(result.to_redacted_dict()))
    return {"checks": 13, "offline": True, "rules_version": 1}


if __name__ == "__main__":
    print(json.dumps(check(), sort_keys=True))
