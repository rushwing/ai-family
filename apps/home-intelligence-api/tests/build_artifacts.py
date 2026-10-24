"""Build three local distributions and verify isolated direct/sdist-derived installs."""

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[3]
PACKAGES = ["libs/state-schema", "toolsets/iot/home-device-fabric", "apps/home-intelligence-api"]


def run(command, *, cwd=ROOT):
    result = subprocess.run(
        [str(x) for x in command], cwd=cwd, check=True, capture_output=True, text=True, timeout=600
    )
    return result.stdout


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--test-results", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    suites = ElementTree.parse(args.test_results).getroot().findall("testsuite")
    count = sum(int(s.attrib["tests"]) for s in suites)
    if count < 1 or any(
        int(s.attrib.get(k, 0)) for s in suites for k in ("failures", "errors", "skipped")
    ):
        raise RuntimeError("required_api_tests_missing_or_not_passing")
    direct, derived, source = [out / name for name in ("direct", "derived", "sdist")]
    records = []
    for package in PACKAGES:
        run(
            [
                sys.executable,
                "-m",
                "build",
                "--no-isolation",
                "--wheel",
                "--outdir",
                direct,
                ROOT / package,
            ]
        )
        run(
            [
                sys.executable,
                "-m",
                "build",
                "--no-isolation",
                "--sdist",
                "--outdir",
                source,
                ROOT / package,
            ]
        )
    extraction = out / "extracted"
    for archive in sorted(source.glob("*.tar.gz")):
        target = extraction / archive.name.removesuffix(".tar.gz")
        target.mkdir(parents=True)
        with tarfile.open(archive) as bundle:
            bundle.extractall(target, filter="data")
        (project,) = target.iterdir()
        run(
            [
                sys.executable,
                "-m",
                "build",
                "--no-isolation",
                "--wheel",
                "--outdir",
                derived,
                project,
            ]
        )
    # Resolve dependencies once; installations and smoke runs are then offline.
    dependencies = out / "dependencies"
    dependencies.mkdir()
    run(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "--only-binary=:all:",
            "--dest",
            dependencies,
            *sorted(direct.glob("*.whl")),
            "httpx>=0.28.1,<0.29",
        ]
    )
    runner = out / "artifact_smoke.py"
    shutil.copyfile(Path(__file__).with_name("artifact_smoke.py"), runner)
    for name, directory in [("direct", direct), ("derived", derived)]:
        env = out / (name + "-env")
        run([sys.executable, "-m", "venv", env])
        python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        run(
            [
                python,
                "-m",
                "pip",
                "install",
                "--no-index",
                "--find-links",
                dependencies,
                *sorted(directory.glob("*.whl")),
                "httpx>=0.28.1,<0.29",
            ],
            cwd=out,
        )
        for flags in [[], ["-O"]]:
            result = json.loads(run([python, "-I", *flags, runner], cwd=out))
            records.append({"distribution": name, "optimized": bool(flags), **result})
    if len({r["openapi_sha256"] for r in records}) != 1:
        raise RuntimeError("installed_schema_mismatch")
    paths = subprocess.check_output(
        [
            "git",
            "ls-files",
            "-co",
            "--exclude-standard",
            "--",
            *PACKAGES,
            ".github/workflows/ci.yml",
        ],
        cwd=ROOT,
        text=True,
    ).splitlines()
    hashes = {
        p: digest(ROOT / p)
        for p in sorted(set(paths))
        if (ROOT / p).is_file() and "__pycache__" not in p
    }
    provenance = {
        "base_commit": run(["git", "rev-parse", "HEAD"]).strip(),
        "source_dirty": bool(run(["git", "status", "--porcelain"]).strip()),
        "source_sha256": hashes,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "test_results_sha256": digest(args.test_results),
        "api_tests": count,
        "smokes": records,
        "artifacts": {
            str(p.relative_to(out)): digest(p)
            for folder in (direct, derived, source, dependencies)
            for p in sorted(folder.iterdir())
            if p.is_file()
        },
    }
    (out / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(json.dumps({"api_tests": count, "installed_smokes": records}, indent=2))


if __name__ == "__main__":
    main()
