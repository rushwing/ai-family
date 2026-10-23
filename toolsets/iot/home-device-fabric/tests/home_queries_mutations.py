"""Reproduce REQ-034 semantic falsifiers in isolated source copies."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "toolsets/iot/home-device-fabric/src"
TESTS = ROOT / "toolsets/iot/home-device-fabric/tests/test_home_queries.py"
MUTATIONS = (
    ("authorization_bypass", "home_queries.py",
     "return _read(lambda: self._store.inventory(context, home_id=home_id))",
     "return self._store._inventories[cast(str, home_id)]"),
    ("ignore_area_filter", "home_queries.py",
     'if area_id is None or row["area_id"] == area_id', 'if True'),
    ("reverse_device_order", "home_queries.py",
     'sorted(selected, key=lambda row: cast(str, row["id"]))',
     'sorted(selected, key=lambda row: cast(str, row["id"]), reverse=True)'),
    ("cross_home_capabilities", "home_queries.py",
     'if home == inventory.home.id and candidate == device:', 'if candidate == device:'),
    ("metadata_creates_device", "home_queries.py",
     'if not any(item.id == device for item in inventory.devices):', 'if False:'),
    ("absent_metadata_is_empty", "home_queries.py",
     'return QueryResult("uninitialized", None)', 'return QueryResult("found", [])'),
    ("exclusive_freshness_boundary", "state_store.py",
     'now - updated <= max_age', 'now - updated < max_age'),
    ("stale_is_fresh", "state_store.py", 'else "stale"', 'else "fresh"'),
    ("duplicate_capability_records", "home_queries.py",
     '(home, device) in keys or type(record["capabilities"]) is not list',
     'type(record["capabilities"]) is not list'),
    ("result_reinitialization", "home_queries.py",
     'if hasattr(self, "_payload"):', 'if False:'),
    ("unlocked_snapshot", "state_store.py",
     'with self._lock:\n            return tuple(', 'if True:\n            return tuple('),
    ("unvalidated_result_data", "home_queries.py",
     'payload = _json({"status": status, "data": data})',
     'payload = json.dumps({"status": status, "data": data})'),
    ("misclassified_identifier", "home_queries.py",
     '"invalid_identifier": "invalid_selector",',
     '"invalid_identifier": "invalid_configuration",'),
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if out.is_relative_to(ROOT):
        raise ValueError("mutation output must be outside checkout")
    out.mkdir(parents=True, exist_ok=False)
    results = []
    for name, filename, old, new in (("baseline", "", "", ""), *MUTATIONS):
        directory = out / name
        shutil.copytree(SOURCE, directory, ignore=shutil.ignore_patterns("__pycache__"))
        if filename:
            target = directory / "home_device_fabric" / filename
            original = target.read_text()
            if original.count(old) != 1:
                raise ValueError("mutation anchor mismatch: " + name)
            target.write_text(original.replace(old, new))
        env = {**os.environ, "PYTHONPATH": str(directory)}
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-c", str(TESTS.parent.parent / "pytest.ini"),
             str(TESTS), "--require-home-queries-runtime", "-q", "--tb=short"],
            env=env, cwd=ROOT, capture_output=True, text=True, timeout=60,
        )
        log = out / (name + ".log")
        log.write_text(result.stdout + result.stderr)
        valid = result.returncode == (0 if name == "baseline" else 1)
        results.append({"mutation": name, "returncode": result.returncode,
                        "detected_or_baseline_passed": valid, "log_sha256": digest(log)})
        print(name, result.returncode, flush=True)
    report = {"source_revision": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_dirty": bool(subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()),
        "runtime_sha256": digest(SOURCE / "home_device_fabric/home_queries.py"),
        "store_sha256": digest(SOURCE / "home_device_fabric/state_store.py"),
        "tests_sha256": digest(TESTS), "results": results}
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return int(not all(row["detected_or_baseline_passed"] for row in results))


if __name__ == "__main__":
    raise SystemExit(main())
