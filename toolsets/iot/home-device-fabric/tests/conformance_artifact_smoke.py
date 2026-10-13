"""Independent installed conformance checks, including an observable driver defect."""

import hashlib
import json
import runpy
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import home_device_fabric.conformance as conformance

EXPECTED_IDS = (
    "discovery",
    "catalogue",
    "provider-binding",
    "provider-arguments",
    "provider-accepted",
    "provider-support",
    "provider-attempt",
    "provider-action",
    "provider-revision",
    "switch-on",
    "switch-off",
    "curtain-closed",
    "curtain-open",
    "curtain-partial",
    "switch-timeout",
    "switch-mismatch",
    "switch-stale",
    "switch-wrong-epoch",
    "switch-deadline-tie",
    "switch-late",
    "curtain-timeout",
    "curtain-mismatch",
    "curtain-stale",
    "curtain-wrong-epoch",
    "curtain-deadline-tie",
    "curtain-late",
    "switch-failed",
    "curtain-failed",
    "switch-offline-unknown",
    "switch-offline-known",
    "curtain-offline-unknown",
    "curtain-offline-known",
    "temperature-offline-unknown",
    "temperature-offline-known",
    "switch-invalid-0",
    "switch-invalid-1",
    "switch-invalid-2",
    "switch-invalid-3",
    "curtain-invalid-0",
    "curtain-invalid-1",
    "curtain-invalid-2",
    "curtain-invalid-3",
    "request-action",
    "request-member",
    "request-revision",
    "temperature-observe",
    "temperature-write",
    "replay",
    "conflict",
    "replay-invalid-type",
    "provider-ordering",
)
HASH = "0cb57579e3eb82bb1d7c73722f1c5e3c386427d45c7efde9ed011a5c7f18e6bd"


def require(condition):
    if not condition:
        raise RuntimeError("installed conformance acceptance failed")


def main():
    require(bool(sys.flags.isolated))
    require(Path(conformance.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()))
    command = [sys.executable, "-I", "-m", "home_device_fabric.conformance"]
    runs = [
        subprocess.run(args, capture_output=True, text=True, timeout=30)
        for args in (command, command, [sys.executable, "-O", *command[1:]])
    ]
    require(all(r.returncode == 0 and r.stderr == "" for r in runs))
    require(runs[0].stdout == runs[1].stdout == runs[2].stdout)
    report = json.loads(runs[0].stdout)
    require(runs[0].stdout == conformance.canonical_json(report) + "\n")
    require(tuple(c["case_id"] for c in report["cases"]) == EXPECTED_IDS)
    require(report["inventory_sha256"] == HASH and report["inventory_version"] == 1)
    require(
        report["counts"] == {"total": 51, "executed": 51, "passed": 51, "failed": 0, "skipped": 0}
    )
    require(conformance.validate_report(report))
    wrappers = runpy.run_path(str(Path(__file__).with_name("conformance_wrappers.py")))
    forwarded = conformance.run_conformance(wrappers["factory"]())
    require(forwarded == report)
    defective = conformance.run_conformance(wrappers["factory"]("identity"))
    discovery = next(c for c in defective["cases"] if c["case_id"] == "discovery")
    require(discovery["status"] == "failed" and discovery["error"] == "identity_mismatch")
    require(defective["passed"] is False and not conformance.validate_report(defective))
    # A forged complete verdict cannot hide missing mandatory results.
    truncated = deepcopy(report)
    truncated["cases"].pop()
    require(not conformance.validate_report(truncated))
    print(
        json.dumps(
            {
                "python": sys.version,
                "executable": sys.executable,
                "optimized": bool(sys.flags.optimize),
                "conformance_smoke": "passed",
                "counts": report["counts"],
                "inventory_sha256": HASH,
                "report_sha256": hashlib.sha256(runs[0].stdout.encode()).hexdigest(),
                "wrapper": "passed",
                "defect_detected": "discovery",
            }
        )
    )


if __name__ == "__main__":
    main()
