"""Run from an isolated installed-wheel interpreter, outside pytest's source path."""

import json
import sys
from pathlib import Path

import state_schema.canonical_state as api
from state_schema.home_inventory import load_inventory

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
    print(
        "Installed-wheel smoke passed: references, ACK rejection, agreement and epoch fencing."
    )


if __name__ == "__main__":
    main()
