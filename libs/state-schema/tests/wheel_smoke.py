"""Run from an isolated installed-wheel interpreter, outside pytest's source path."""

import json
import sys
from pathlib import Path

import state_schema.canonical_state as api
import state_schema.capability as capabilities
from state_schema.home_inventory import load_inventory
from state_schema.initial_capabilities import load_initial_capabilities

ROOT = Path(__file__).resolve().parents[3]


def main():
    assert Path(api.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()), (
        "Smoke must import the installed wheel, not the source checkout"
    )
    examples = ROOT / "docs/product/home-intelligence/examples"
    fixture = json.loads((examples / "canonical-state-timeline.example.json").read_text())
    inventory = load_inventory(examples / "three-bedroom-apartment.example.json")
    data = api.validate_states(
        {"schema_version": 1, "states": [fixture["initial_state"]]}, inventory=inventory
    )["states"][0]
    assert api.evaluate_convergence(data, current_epoch=1) == "unknown"
    # Passing raw ACK through a declared observation boundary must fail.
    try:
        api.apply_state_update(data, current_epoch=1, availability=fixture["provider_ack"])
    except api.StateError:
        pass
    else:
        raise AssertionError("ACK accepted as availability evidence")
    for update, expected in zip(fixture["observations"], ["pending", "confirmed"], strict=True):
        data = api.apply_state_update(data, current_epoch=1, **update)
        assert api.evaluate_convergence(data, current_epoch=1) == expected
    assert data["reported_state"]["power"]["value"] is False
    assert type(data["reported_state"]["level"]["value"]) is int
    for operation in (
        lambda: api.apply_state_update(
            data, current_epoch=2, reported_state=fixture["observations"][1]["reported_state"]
        ),
        lambda: api.validate_state({**data, "converged": True}),
    ):
        try:
            operation()
        except api.StateError:
            pass
        else:
            raise AssertionError("Invalid generation/completion field accepted")
    assert Path(capabilities.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
    catalogue = capabilities.load_capabilities_json(
        (examples / "capability-base.example.json").read_text()
    )
    payload = {"power": False}
    assert (
        catalogue.validate_payload("demo.power", 1, "action_input", "set_power", payload) == payload
    )
    assert catalogue.validate_payload(
        "demo.power", 1, "action_output", "set_power", {"accepted": True}
    ) == {"accepted": True}
    for operation in (
        lambda: catalogue.get("demo.power", 2),
        lambda: catalogue.validate_payload(
            "demo.power", 1, "action_input", "set_power", {"power": 0}
        ),
        lambda: capabilities.load_capability_json('{"private":1,"private":2}'),
        lambda: capabilities.validate_schema({"type": "string", "$ref": "private"}),
    ):
        try:
            operation()
        except capabilities.CapabilityError:
            pass
        else:
            raise AssertionError("Invalid Capability version/payload/schema/text accepted")
    import state_schema.initial_capabilities as initial

    assert Path(initial.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
    loaded = load_initial_capabilities()
    expected = (
        ("home.switchable", "is_on", False),
        ("home.positionable", "position_percent", 50),
        ("home.temperature_sensor", "temperature_c", -273.15),
        ("home.humidity_sensor", "relative_humidity_percent", 45.5),
        ("home.power_meter", "power_w", -125.5),
        ("home.battery_powered", "battery_percent", 62.5),
    )
    assert [(item.capability_id, item.capability_version) for item in loaded.capabilities] == [
        (identity, 1) for identity, _, _ in expected
    ]
    for identity, member, value in expected:
        assert loaded.validate_payload(identity, 1, "property", member, value) == value
        for invalid in (None, "unknown"):
            try:
                loaded.validate_payload(identity, 1, "property", member, invalid)
            except capabilities.CapabilityError:
                pass
            else:
                raise AssertionError("Invalid initial measurement accepted")
    for operation in (
        lambda: loaded.get("home.switchable", 2),
        lambda: loaded.validate_payload(
            "home.positionable", 1, "property", "position_percent", 50.0
        ),
        lambda: loaded.validate_payload(
            "home.positionable", 1, "action_input", "set_position", {"position_percent": 101}
        ),
        lambda: loaded.validate_payload("home.temperature_sensor", 1, "action_input", "set_on", {}),
        lambda: loaded.validate_payload(
            "home.switchable", 1, "action_output", "set_on", {"accepted": True}
        ),
    ):
        try:
            operation()
        except capabilities.CapabilityError:
            pass
        else:
            raise AssertionError("Invalid initial capability selection/payload accepted")
    assert loaded.validate_payload(
        "home.switchable", 1, "action_input", "set_on", {"is_on": False}
    ) == {"is_on": False}
    assert loaded.validate_payload("home.switchable", 1, "action_output", "set_on", None) is None
    snapshot = loaded.to_dict()
    snapshot["capabilities"].clear()
    assert len(loaded.capabilities) == len(load_initial_capabilities().capabilities) == 6
    import state_schema.action_contracts as actions

    assert Path(actions.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
    request = {
        "schema_version": 1, "home_id": "home-example",
        "device_id": "device-bedroom-light-01", "capability_id": "home.switchable",
        "capability_version": 1, "action_id": "set_on", "arguments": {"is_on": False},
        "idempotency_key": "wheel-key", "trace_id": "wheel-trace",
    }
    context = {"home_id": "home-example", "subject_id": "wheel-subject",
               "family_member_id": "wheel-member", "role": "adult"}
    cat = loaded.to_dict()
    task = actions.create_task(request, requester=context, task_id="wheel-task",
                               inventory=inventory, catalogue=cat)
    identity = {k: request[k] for k in (
        "home_id", "device_id", "capability_id", "capability_version", "action_id")}
    correlation = {"task_id": task["task_id"], "trace_id": task["trace_id"], **identity}
    out = {"schema_version": 1, **correlation, "state": "running",
           "output": {"present": True, "value": None}, "error": None,
           "evidence": {"kind": "ack", **correlation}, "physical_outcome": "unverified"}
    task = actions.transition_task(task, out, inventory=inventory, catalogue=cat,
                                   dispatch_context={"current_epoch": 1,
                                                     "baseline": {"epoch": 1, "sequence": 1}})
    assert actions.validate_task(task, inventory=inventory, catalogue=cat) == task
    assert actions.ActionRequest.from_dict(request).to_dict() == request
    assert actions.Task.from_dict(task).to_dict() == task
    assert actions.ActionResult.from_dict(out).to_dict() == out
    try:
        actions.transition_task(task, {**out, "state": "succeeded",
                                      "physical_outcome": "confirmed"},
                                inventory=inventory, catalogue=cat)
    except actions.ActionError:
        pass
    else:
        raise AssertionError("Installed Action contract treated ACK as success")
    observed = {"home_id": request["home_id"], "device_id": request["device_id"],
                "desired_state": None, "reported_state": {"is_on": {
                    "status": "known", "value": False,
                    "observed_at": "2026-01-01T12:00:00Z",
                    "ordering": {"epoch": 1, "sequence": 2}}},
                "availability": {"status": "online", "observed_at": "2026-01-01T12:00:00Z",
                                 "ordering": {"epoch": 1, "sequence": 2}}}
    done = actions.transition_task(task, {**out, "state": "succeeded",
                                          "physical_outcome": "confirmed",
                                          "evidence": {"kind": "state", **correlation,
                                                       "state": observed}},
                                   inventory=inventory, catalogue=cat)
    assert done["state"] == "succeeded"
    assert actions.compare_idempotency(done, {**request, "trace_id": "new-trace"},
                                       requester=context, inventory=inventory,
                                       catalogue=cat) == "replay"
    print("Installed-wheel smoke passed: State, Capability, catalogue and Action contracts.")


if __name__ == "__main__":
    main()
