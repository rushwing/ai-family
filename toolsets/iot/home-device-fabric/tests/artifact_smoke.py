"""Execute with python -I outside the checkout using installed wheel pairs."""

import json
import runpy
import sys
from pathlib import Path

import home_device_fabric
import state_schema.action_contracts as actions
import state_schema.provider_contracts as contracts
from home_device_fabric import MockProvider, ProviderProtocol
from state_schema.canonical_state import apply_state_update


def main():
    for module in (home_device_fabric, actions, contracts):
        assert Path(module.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
    assert sys.flags.isolated
    # Explicit fictional test data only; no sys.path injection or runtime source loading.
    f = runpy.run_path(str(Path(__file__).with_name("fixtures.py")))
    c = f["config"]()
    t = f["task"](c)
    f["script"](
        c,
        t,
        [
            f["delivery"](0, f["outcome"](t), True),
            f["delivery"](10, f["input_record"]("availability")),
            f["delivery"](10, f["input_record"](correlated=f["correlation"](t))),
        ],
    )
    p = MockProvider(c)
    assert isinstance(p, ProviderProtocol)
    registration = p.discover()[0]
    assert registration.binding.to_dict() == f["binding"]()
    assert contracts.DeviceRegistration.from_dict(
        registration.to_dict(), configuration=contracts.MockConfiguration.from_dict(c)
    ) == registration
    state = p.snapshot()[0].to_dict()
    p.submit(t, binding=f["binding"](), attempt_id="attempt-1")
    times = []
    for item in p.advance(100000):
        times.append(item.time_ms)
        if item.outcome:
            actions.validate_result(
                item.outcome.result.to_dict(),
                task=t,
                inventory=c["inventory"],
                catalogue=c["catalogue"],
            )
            assert t["state"] == "running", "ACK must not establish success"
        if item.input:
            inp = item.input.to_dict()
            state = apply_state_update(
                state,
                current_epoch=1,
                reported_state={inp["member"]: inp["payload"]}
                if inp["kind"] == "property"
                else None,
                availability=inp["payload"] if inp["kind"] == "availability" else None,
            )
            if inp["correlation"]:
                evidence = {**f["evidence"](t, "state"), "state": state}
                t = actions.transition_task(
                    t,
                    f["result"](t, "succeeded", evidence),
                    inventory=c["inventory"],
                    catalogue=c["catalogue"],
                )
                p.settle(t)
    assert times == [0, 10, 10]
    assert t["state"] == "succeeded" and t["result"]["physical_outcome"] == "confirmed"
    assert state["reported_state"]["is_on"]["value"] is False
    assert len(p.dispatch_log) == 1 and list(p.advance(100000)) == []
    print(json.dumps({"python": sys.version, "executable": sys.executable, "smoke": "passed"}))


if __name__ == "__main__":
    main()
