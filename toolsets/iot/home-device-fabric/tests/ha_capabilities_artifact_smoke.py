"""Installed REQ-033 checks also execute under isolated optimized Python."""

import copy
import json


def check():
    from home_device_fabric.ha_capabilities import HACapabilityError, HACapabilityInferrer
    from home_device_fabric.ha_mapping import HARegistryMapper
    from state_schema.capability import CapabilityDescriptor

    checks = 0

    def require(condition):
        nonlocal checks
        if not condition:
            raise RuntimeError("installed_capabilities_check_failed")
        checks += 1

    config = {
        "schema_version": 1,
        "home": {"id": "home-example", "name": "Example", "residence_type": "other"},
        "provider_instance_id": "ha-example", "area_ids": {},
        "device_ids": {"raw-device": "device-example"}, "entity_ids": {},
    }
    states = [
        {"entity_id": "switch.example", "state": "off", "attributes": {}},
        {"entity_id": "cover.example", "state": "unknown", "attributes": {
            "supported_features": 4}},
    ]
    for kind, unit in (("temperature", "°C"), ("humidity", "%"), ("power", "W"), ("battery", "%")):
        states.append({"entity_id": "sensor." + kind, "state": "unavailable", "attributes": {
            "device_class": kind, "unit_of_measurement": unit}})
    data = {"devices": [{"id": "raw-device"}], "areas": [], "states": states,
            "entities": [{"entity_id": row["entity_id"], "device_id": "raw-device"}
                         for row in states]}
    mapped = HARegistryMapper(config).map(data).for_adapter()
    engine = HACapabilityInferrer(provider_instance_id="ha-example")
    result = engine.infer(**mapped, discovery=data)
    exported = result.for_adapter()
    rows = exported["devices"][0]["capabilities"]
    require([row["descriptor"]["capability_id"] for row in rows] == [
        "home.battery_powered", "home.humidity_sensor", "home.positionable",
        "home.power_meter", "home.switchable", "home.temperature_sensor"])
    for row in rows:
        descriptor = CapabilityDescriptor.from_dict(row["descriptor"])
        require(set(row["provider_mapping"]["actions"]) == set(dict(descriptor.actions)))
    require(rows[4]["provider_mapping"]["actions"]["set_on"]["services"] == {
        "true": "turn_on", "false": "turn_off"})
    require(rows[2]["provider_mapping"]["actions"]["set_position"]["parameters"] == {
        "position": {"input": "position_percent"}})
    changed = copy.deepcopy(data)
    changed["states"][1]["attributes"]["supported_features"] = 3
    require(len(engine.infer(**mapped, discovery=changed).for_adapter()["devices"][0][
        "capabilities"]) == 5)
    changed["states"][2]["attributes"]["unit_of_measurement"] = "°F"
    require(len(engine.infer(**mapped, discovery=changed).for_adapter()["devices"][0][
        "capabilities"]) == 4)
    require(HACapabilityInferrer(provider_instance_id="ha-other").infer(
        **mapped, discovery=data).for_adapter()["devices"][0]["capabilities"] == [])
    changed = copy.deepcopy(data)
    changed["states"].reverse()
    require(engine.infer(**mapped, discovery=changed).for_adapter() == exported)
    exported["devices"].clear()
    require(len(result.for_adapter()["devices"]) == 1)
    changed["entities"][0]["device_id"] = "private-wrong-parent"
    try:
        engine.infer(**mapped, discovery=changed)
    except HACapabilityError as error:
        require(error.code == "invalid_bindings" and error.__context__ is None)
    else:
        raise RuntimeError("installed_capabilities_check_failed")
    require("raw-device" not in repr(engine) + repr(result)
            + json.dumps(result.to_redacted_dict()))
    return {"checks": checks, "offline": True, "rules_version": 1}


if __name__ == "__main__":
    print(json.dumps(check(), sort_keys=True))
