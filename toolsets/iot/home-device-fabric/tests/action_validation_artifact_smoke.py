"""Installed REQ-037 checks; explicit assertions also execute under -O -I."""
import json


def configuration():
    from state_schema.initial_capabilities import load_initial_capabilities

    catalogue = load_initial_capabilities().capabilities
    home = {"id": "home-example", "name": "Fictional", "residence_type": "other"}
    inventory = {"schema_version": 1, "home": home, "floors": [], "areas": [],
                 "labels": [], "area_groups": [], "devices": [
                     {"id": f"device-{i}", "home_id": home["id"], "name": "Fixture",
                      "area_id": None, "labels": []} for i in range(8)]}
    metadata = [{"home_id": home["id"], "device_id": f"device-{i}",
                 "capabilities": [descriptor.to_dict()]}
                for i, descriptor in enumerate(catalogue)]
    metadata.append({"home_id": home["id"], "device_id": "device-6", "capabilities": []})
    return {"registered_inventory": inventory, "capabilities": metadata}


def request(**changes):
    return {"schema_version": 1, "home_id": "home-example", "device_id": "device-0",
            "capability_id": "home.switchable", "capability_version": 1,
            "action_id": "set_on", "arguments": {"is_on": True},
            "idempotency_key": "key-example", "trace_id": "trace-example", **changes}


def check():
    from home_device_fabric.action_validation import ActionValidator

    checks = 0

    def require(value):
        nonlocal checks
        if not value:
            raise RuntimeError("installed_action_validation_check_failed")
        checks += 1

    validator = ActionValidator(**configuration())
    success = validator.validate(request())
    require(success.to_dict() == {"status": "valid", "failure_code": None, "request": request()})
    require(validator.validate(request(device_id="device-1", capability_id="home.positionable",
        action_id="set_position", arguments={"position_percent": 100})).status == "valid")
    for changes, expected in [
        ({"home_id": "home-other"}, "unknown_home"),
        ({"device_id": "device-absent"}, "unknown_device"),
        ({"device_id": "device-7"}, "capabilities_uninitialized"),
        ({"device_id": "device-6"}, "unknown_capability"),
        ({"capability_id": "vendor.unlock"}, "unknown_capability"),
        ({"capability_version": 2}, "unsupported_capability_version"),
        ({"action_id": "toggle"}, "unknown_action"),
        ({"arguments": {"is_on": 1}}, "invalid_arguments"),
    ]:
        result = validator.validate(request(**changes))
        require(result.to_dict() == {"status": "rejected", "failure_code": expected,
                                     "request": None})
    for i, capability in enumerate(("home.temperature_sensor", "home.humidity_sensor",
                                   "home.power_meter", "home.battery_powered"), start=2):
        require(validator.validate(request(device_id=f"device-{i}", capability_id=capability,
            action_id="set_value")).failure_code == "read_only_capability")
    for arguments in ({"position_percent": -1}, {"position_percent": 101},
                      {"position_percent": 0.5}, {"position_percent": True}):
        require(validator.validate(request(device_id="device-1", capability_id="home.positionable",
            action_id="set_position", arguments=arguments)).failure_code == "invalid_arguments")
    require(validator.validate({"private": "secret"}).failure_code == "invalid_request")
    require(ActionValidator(**configuration(), max_input_bytes=1).validate(request()).failure_code
            == "input_too_large")
    exported = success.to_dict()
    exported["request"]["arguments"]["is_on"] = False
    require(success.to_dict()["request"]["arguments"]["is_on"] is True)
    require(repr(success) == "ActionValidationResult()" and repr(validator) == "ActionValidator()")
    return {"checks": checks, "offline": True}


if __name__ == "__main__":
    print(json.dumps(check(), sort_keys=True))
