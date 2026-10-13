"""Independent installed CLI assertions, run with -I outside the checkout."""

import json
import subprocess
import sys
from pathlib import Path

import home_device_fabric.caller
import home_device_fabric.demo
import home_device_fabric.scenarios

COMMANDS = (
    ("switch", "success"), ("curtain", "success"), ("temperature", "observe"),
    ("switch", "timeout"), ("switch", "offline"),
    ("curtain", "invalid-position"), ("temperature", "write-rejected"),
)


def check(data, device, scenario):
    assert data["schema_version"] == 1 and data["simulation"] is True
    assert data["device"] == device and data["scenario"] == scenario
    assert len(data["discovery"]) == 3
    cases = data["cases"]
    if scenario == "success":
        member = "is_on" if device == "switch" else "position_percent"
        targets = [True, False] if device == "switch" else [0, 100, 40]
        assert len(cases) == data["dispatch_count"] == len(targets)
        for case, target in zip(cases, targets):
            assert case["dispatch_count"] == 1 and case["task"]["state"] == "succeeded"
            assert case["result"]["physical_outcome"] == "confirmed"
            value = case["final_state"]["reported_state"][member]["value"]
            assert type(value) is type(target) and value == target
    elif scenario == "observe":
        assert data["dispatch_count"] == 0 and cases[0]["task"] is None
        assert data["units"] == {"temperature_c": "degrees_celsius"}
        assert cases[0]["final_state"]["reported_state"]["temperature_c"]["value"] == 21.25
    elif scenario == "timeout":
        assert cases[0]["task"]["state"] == "timed_out" and data["dispatch_count"] == 1
        assert cases[0]["result"]["error"]["code"] == "provider_timeout"
        assert cases[0]["result"]["physical_outcome"] == "unverified"
    else:
        code = "offline" if scenario == "offline" else "invalid_request"
        assert data["dispatch_count"] == 0
        assert all(c["rejection"]["code"] == code and c["task"] is None for c in cases)


def main():
    assert sys.flags.isolated
    for module in (home_device_fabric.caller, home_device_fabric.demo,
                   home_device_fabric.scenarios):
        assert Path(module.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
    runs = []
    for device, scenario in COMMANDS:
        args = ["-I", "-m", "home_device_fabric.demo", "--device", device, "--scenario", scenario]
        first = subprocess.run([sys.executable, *args], capture_output=True, text=True, check=True)
        repeat = subprocess.run([sys.executable, *args], capture_output=True, text=True, check=True)
        optimized = subprocess.run([sys.executable, "-O", *args], capture_output=True,
                                   text=True, check=True)
        assert first.stderr == repeat.stderr == optimized.stderr == ""
        assert first.stdout == repeat.stdout == optimized.stdout
        data = json.loads(first.stdout)
        assert first.stdout == json.dumps(data, sort_keys=True, separators=(",", ":"),
                                         allow_nan=False) + "\n"
        check(data, device, scenario)
        runs.append({"device": device, "scenario": scenario, "cases": len(data["cases"]),
                     "dispatch_count": data["dispatch_count"], "repeat_and_optimized": "passed"})
    print(json.dumps({"python": sys.version, "executable": sys.executable,
                      "demo_smoke": "passed", "runs": runs}))


if __name__ == "__main__":
    main()
