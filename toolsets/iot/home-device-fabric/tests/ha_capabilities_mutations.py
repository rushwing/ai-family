"""Reproduce REQ-033 assertion-detected mutations in disposable package copies."""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "toolsets/iot/home-device-fabric/src/home_device_fabric"
TEST = ROOT / "toolsets/iot/home-device-fabric/tests/test_ha_capabilities.py"
MUTATIONS = (
    ("wrong_unit", '("temperature", "°C"):', '("temperature", "°F"):'),
    ("missing_position_support", "and features & 4:", ":"),
    ("missing_feature_upper_bound", "0 <= features <= 2147483647", "0 <= features"),
    ("extra_sensor_action", '    return {}\n', '    return {"unexpected_action": {}}\n'),
    ("coerce_float_features",
     "type(features) is int and 0 <= features <= 2147483647 and features & 4",
     "type(features) in (int, float) and 0 <= features <= 2147483647 and int(features) & 4"),
    ("cross_instance",
     'if binding.provider != "ha" or binding.provider_instance_id != self._instance:',
     'if binding.provider != "ha":'),
    ("wrong_parent", 'or row.get("device_id") != mapping.device_registry_id', 'or False'),
    ("disabled_entity", 'or row.get("disabled_by") is not None', 'or False'),
    ("ambiguity_first_wins", "if len(entries) != 1:", "if False:"),
    ("reverse_switch", '\"true\": \"turn_on\", \"false\": \"turn_off\"',
     '\"true\": \"turn_off\", \"false\": \"turn_on\"'),
    ("wrong_position_parameter", '\"position\": {\"input\": \"position_percent\"}',
     '\"position\": {\"input\": \"wrong_parameter\"}'),
    ("result_reinitialization", 'if hasattr(self, "_payload"):', 'if False:'),
    ("unordered_capabilities", "in sorted(candidates.items()):", "in candidates.items():"),
)



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    output = args.out_dir.resolve()
    if output.is_relative_to(ROOT):
        raise ValueError("mutation output must be outside the checkout")
    output.mkdir(parents=True, exist_ok=True)
    original = (PACKAGE / "ha_capabilities.py").read_text()
    reports = []
    cases = (("baseline", None, None), *MUTATIONS)
    for label, before, after in cases:
        with tempfile.TemporaryDirectory(prefix="req033-mutation-") as temporary:
            directory = Path(temporary)
            shutil.copytree(PACKAGE, directory / "home_device_fabric",
                            ignore=shutil.ignore_patterns("__pycache__"))
            if before is not None:
                if before not in original:
                    raise RuntimeError("mutation anchor missing: " + label)
                (directory / "home_device_fabric/ha_capabilities.py").write_text(
                    original.replace(before, after, 1))
            bootstrap = (
                "import sys; sys.path.insert(0, sys.argv[1]); import pytest; "
                "raise SystemExit(pytest.main(sys.argv[2:]))"
            )
            command = [sys.executable, "-I", "-c", bootstrap, str(directory),
                       "-c", str(ROOT / "toolsets/iot/home-device-fabric/pytest.ini"),
                       str(TEST), "--require-ha-capabilities-runtime", "-q"]
            result = subprocess.run(command, cwd=directory, capture_output=True,
                                    text=True, timeout=90)
            log = result.stdout + result.stderr
            (output / (label + ".log")).write_text(log)
            expected = 0 if before is None else 1
            if result.returncode != expected or (before is not None and "FAILED " not in log):
                raise RuntimeError("mutation verification failed: " + label)
            reports.append({"mutation": label, "before": before, "after": after,
                            "returncode": result.returncode,
                            "log_sha256": hashlib.sha256(log.encode()).hexdigest(),
                            "summary": [line for line in log.splitlines()
                                        if "passed" in line or line.startswith("FAILED ")]})
    report = {"runtime_sha256": hashlib.sha256(original.encode()).hexdigest(),
              "tests_sha256": hashlib.sha256(TEST.read_bytes()).hexdigest(),
              "python": sys.version, "results": reports}
    (output / "mutations.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"baseline_passed": True, "detected_mutations": len(MUTATIONS)}))


if __name__ == "__main__":
    main()
