"""Installed REQ-038 checks, including real mapper/inference, also under -O -I."""

import copy
import json


def configuration():
    from home_device_fabric.ha_capabilities import HACapabilityInferrer
    from home_device_fabric.ha_mapping import HARegistryMapper

    config = {"schema_version": 1,
              "home": {"id": "home-example", "name": "Fictional", "residence_type": "other"},
              "provider_instance_id": "ha-example", "area_ids": {}, "entity_ids": {},
              "device_ids": {"raw-group": "device-example", "raw-other": "device-other"}}
    states = [{"entity_id": "switch.example", "state": "off", "attributes": {}},
              {"entity_id": "cover.example", "state": "unknown", "attributes": {
                  "supported_features": 4}}]
    for kind, unit in (("temperature", "°C"), ("humidity", "%"), ("power", "W"), ("battery", "%")):
        states.append({"entity_id": "sensor." + kind, "state": "unavailable", "attributes": {
            "device_class": kind, "unit_of_measurement": unit}})
    discovery = {"areas": [], "devices": [{"id": "raw-group"}, {"id": "raw-other"}],
                 "states": states + [{"entity_id": "switch.other", "state": "on",
                                       "attributes": {}}],
                 "entities": [{"entity_id": row["entity_id"], "device_id": "raw-group"}
                              for row in states] + [
                     {"entity_id": "switch.other", "device_id": "raw-other"}]}
    mapped = HARegistryMapper(config).map(discovery).for_adapter()
    projection = HACapabilityInferrer(provider_instance_id="ha-example").infer(
        **mapped, discovery=discovery).for_adapter()
    return {"registered_inventory": mapped["inventory"], "bindings": mapped["bindings"],
            "capability_projection": projection, "provider_instance_id": "ha-example"}


def request(**changes):
    return {"schema_version": 1, "home_id": "home-example", "device_id": "device-example",
            "capability_id": "home.switchable", "capability_version": 1,
            "action_id": "set_on", "arguments": {"is_on": True},
            "idempotency_key": "key-example", "trace_id": "trace-example", **changes}


def entry(config, capability="home.switchable", device="device-example"):
    rows = next(row["capabilities"] for row in config["capability_projection"]["devices"]
                if row["device_id"] == device)
    return next(row for row in rows if row["descriptor"]["capability_id"] == capability)


def check():
    from home_device_fabric.action_resolution import ActionResolver

    checks = 0

    def require(condition):
        nonlocal checks
        if not condition:
            raise RuntimeError("installed_action_resolution_check_failed")
        checks += 1

    config = configuration()
    resolver = ActionResolver(**config)
    for value in (True, False):
        raw = request(arguments={"is_on": value})
        result = resolver.resolve(raw)
        require(result.for_adapter() == {"status": "resolved", "failure_code": None,
            "request": raw, "operation": {"provider": "ha", "provider_instance_id": "ha-example",
            "domain": "switch", "service": "turn_on" if value else "turn_off",
            "target": {"entity_id": "switch.example"}, "service_data": {}}})
    for value in (0, 50, 100):
        result = resolver.resolve(request(capability_id="home.positionable",
            action_id="set_position", arguments={"position_percent": value}))
        require(result.for_adapter()["operation"] == {"provider": "ha",
            "provider_instance_id": "ha-example", "domain": "cover",
            "service": "set_cover_position",
            "target": {"entity_id": "cover.example"}, "service_data": {"position": value}})
    for changes, code in [({"home_id": "home-other"}, "unknown_home"),
        ({"device_id": "missing"}, "unknown_device"),
        ({"capability_id": "vendor.private"}, "unknown_capability"),
        ({"capability_version": 2}, "unsupported_capability_version"),
        ({"action_id": "toggle"}, "unknown_action"),
        ({"arguments": {"is_on": 1}}, "invalid_arguments"),
        ({"extra": "private"}, "invalid_request")]:
        require(resolver.resolve(request(**changes)).for_adapter() == {
            "status": "rejected", "failure_code": code, "request": None, "operation": None})
    for capability in ("home.temperature_sensor", "home.humidity_sensor", "home.power_meter",
                       "home.battery_powered"):
        require(resolver.resolve(request(capability_id=capability)).failure_code ==
                "read_only_capability")
    altered = copy.deepcopy(config)
    altered["bindings"]["bindings"] = []
    require(ActionResolver(**altered).resolve(request()).failure_code == "missing_binding")
    altered = copy.deepcopy(config)
    altered["provider_instance_id"] = "ha-other"
    require(ActionResolver(**altered).resolve(request()).failure_code == "provider_mismatch")
    for field, value in (("entity_id", "switch.other"), ("provider_instance_id", "ha-other"),
                         ("actions", {}), ("extra", "secret")):
        altered = copy.deepcopy(config)
        entry(altered)["provider_mapping"][field] = value
        require(ActionResolver(**altered).resolve(request()).failure_code ==
                "invalid_provider_mapping")
    altered = copy.deepcopy(config)
    entry(altered)["provider_mapping"] = None
    require(ActionResolver(**altered).resolve(request()).failure_code == "mapping_uninitialized")
    require(ActionResolver(**config, max_input_bytes=1).resolve(request()).failure_code ==
            "input_too_large")
    result = resolver.resolve(request())
    exported = result.for_adapter()
    exported["operation"]["target"]["entity_id"] = "switch.private"
    require(result.for_adapter()["operation"]["target"]["entity_id"] == "switch.example")
    require(result.to_redacted_dict() == {"status": "resolved", "failure_code": None})
    require(repr(result) == "ActionResolutionResult()" and repr(resolver) == "ActionResolver()")
    return {"checks": checks, "offline": True}


if __name__ == "__main__":
    print(json.dumps(check(), sort_keys=True))
