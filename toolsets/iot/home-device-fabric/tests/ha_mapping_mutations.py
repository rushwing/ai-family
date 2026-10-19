"""Reproduce REQ-032 assertion-detected mutations in disposable package copies."""

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
TEST = ROOT / "toolsets/iot/home-device-fabric/tests/test_ha_mapping.py"
MUTATIONS = (
    ("ambiguous_identity", "if identity in assigned:", "if False:"),
    ("last_entity_only", "grouped.setdefault(parent, []).append(raw_id)",
     "grouped[parent] = [raw_id]"),
    ("disabled_entity_included", 'if record.get("disabled_by") is not None:', "if False:"),
    ("unsorted_binding_members", '"entity_ids": sorted(members)', '"entity_ids": members'),
    ("drop_spatial_assignment", "area_ids.get(raw_area) if raw_area is not None else None",
     "None"),
    ("skip_state_validation", "if type(state) is not str or len(state) > 4096:", "if False:"),
    ("allow_result_reinitialization", 'if hasattr(self, "_inventory"):', "if False:"),
    ("allow_aliased_objects", "if id(item) in seen:", "if False:"),
    ("result_counter_type", "type(count) is not int or not 0 <= count <= 10000",
     "not 0 <= count <= 10000"),
    ("result_counter_length", "or len(counts) != len(_COUNT_KEYS)", "or False"),
    ("result_cardinalities",
     "if counts[:3] != (len(canonical.areas), len(canonical.devices), len(bound.bindings)):",
     "if False:"),
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    output = args.out_dir.resolve()
    if output.is_relative_to(ROOT):
        raise ValueError("mutation output must be outside the checkout")
    output.mkdir(parents=True, exist_ok=True)
    original = (PACKAGE / "ha_mapping.py").read_text()
    reports = []
    cases = (("baseline", None, None), *MUTATIONS)
    for label, before, after in cases:
        with tempfile.TemporaryDirectory(prefix="req032-mutation-") as temporary:
            directory = Path(temporary)
            shutil.copytree(PACKAGE, directory / "home_device_fabric",
                            ignore=shutil.ignore_patterns("__pycache__"))
            if before is not None:
                if before not in original:
                    raise RuntimeError("mutation anchor missing: " + label)
                (directory / "home_device_fabric/ha_mapping.py").write_text(
                    original.replace(before, after, 1))
            bootstrap = (
                "import sys; sys.path.insert(0, sys.argv[1]); import pytest; "
                "raise SystemExit(pytest.main(sys.argv[2:]))"
            )
            command = [sys.executable, "-I", "-c", bootstrap, str(directory),
                       "-c", str(ROOT / "toolsets/iot/home-device-fabric/pytest.ini"),
                       str(TEST), "--require-ha-mapping-runtime", "-q"]
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
