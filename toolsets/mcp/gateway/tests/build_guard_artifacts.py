"""Build direct/sdist-derived local wheel sets and run isolated PG guard smokes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import venv
from pathlib import Path

from build import ProjectBuilder

ROOT = Path(__file__).resolve().parents[4]
PACKAGES = (
    "libs/state-schema",
    "toolsets/iot/home-device-fabric",
    "toolsets/mcp/goal-mcp",
    "toolsets/mcp/gateway",
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if out.is_relative_to(ROOT):
        raise ValueError("artifact_directory_must_be_outside_checkout")
    dsn = os.environ.get("AIFAMILY_CONFIRMATION_TEST_DSN")
    if not dsn:
        raise ValueError("dedicated_postgresql_required")
    out.mkdir(parents=True, exist_ok=True)
    direct, derived = [], []
    for package in PACKAGES:
        builder = ProjectBuilder(str(ROOT / package))
        direct.append(Path(builder.build("wheel", str(out / "direct"))))
        sdist = builder.build("sdist", str(out / "sdist"))
        with tempfile.TemporaryDirectory(dir=out) as folder:
            with tarfile.open(sdist) as archive:
                archive.extractall(folder, filter="data")
            paths = list(Path(folder).iterdir())
            if len(paths) != 1:
                raise RuntimeError("invalid_sdist")
            derived.append(Path(ProjectBuilder(str(paths[0])).build("wheel", str(out / "derived"))))
    wheelhouse = out / "dependencies"
    wheelhouse.mkdir(exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "--only-binary=:all:",
            "--timeout",
            "20",
            "--retries",
            "1",
            "--index-url",
            "https://pypi.org/simple",
            "--dest",
            str(wheelhouse),
            *map(str, direct),
        ],
        check=True,
        capture_output=True,
    )
    results, audit_results = [], []
    for kind, wheels in (("direct", direct), ("derived", derived)):
        directory = out / (kind + "-env")
        venv.EnvBuilder(with_pip=True).create(directory)
        python = directory / "bin/python"
        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--no-index",
                "--find-links",
                str(wheelhouse),
                *map(str, wheels),
            ],
            check=True,
            capture_output=True,
        )
        for optimized in (False, True):
            command = [str(python), "-I"] + (["-O"] if optimized else [])
            command.append(str(Path(__file__).with_name("installed_guard_smoke.py")))
            run = subprocess.run(
                command,
                input=json.dumps({"dsn": dsn, "root": str(ROOT)}),
                text=True,
                capture_output=True,
                cwd=out,
                timeout=90,
            )
            if run.returncode:
                raise RuntimeError("installed_guard_smoke_failed")
            result = json.loads(run.stdout)
            if result["checks"] != 19 or result["dispatch_enabled"] is not False:
                raise RuntimeError("incomplete_installed_guard_evidence")
            results.append({"wheel_set": kind, "optimized": optimized, **result})
            audit_command = command[:-1] + [
                str(Path(__file__).with_name("installed_audit_smoke.py"))
            ]
            audit_run = subprocess.run(
                audit_command,
                input=json.dumps({"dsn": dsn, "root": str(ROOT)}),
                text=True, capture_output=True, cwd=out, timeout=90,
            )
            if audit_run.returncode:
                raise RuntimeError("installed_audit_smoke_failed")
            audit_result = json.loads(audit_run.stdout)
            if audit_result["checks"] != 25 or audit_result["dispatch_enabled"] is not False:
                raise RuntimeError("incomplete_installed_audit_evidence")
            audit_results.append({"wheel_set": kind, "optimized": optimized, **audit_result})
    report = {
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "python": sys.version,
        "smokes": results,
        "audit_smokes": audit_results,
        "sha256": {
            str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ("direct", "sdist", "derived", "dependencies")
            for p in sorted((out / folder).glob("*"))
            if p.is_file()
        },
    }
    (out / "provenance.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps({"smokes": results, "audit_smokes": audit_results,
                    "distributions": len(direct) + len(derived) + len(PACKAGES)})
    )


if __name__ == "__main__":
    main()
