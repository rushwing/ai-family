"""Build both distributions and verify isolated direct/sdist-derived wheel pairs.

Run in an environment with build, hatchling and pip installed. Builds use no
isolation. Resolve HTTPX's dependency wheels once, then install each compatible
package pair and that recorded closure offline into fresh smoke environments.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import venv
from pathlib import Path

from build import ProjectBuilder

ROOT = Path(__file__).resolve().parents[4]
PACKAGES = (ROOT / "libs/state-schema", ROOT / "toolsets/iot/home-device-fabric")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.out_dir.resolve()
    assert not output.is_relative_to(ROOT), "Artifacts and smoke must run outside the checkout"
    output.mkdir(parents=True, exist_ok=True)
    dependencies = output / "dependencies"
    dependencies.mkdir(exist_ok=True)
    subprocess.run(
        [sys.executable, "-m", "pip", "download", "--only-binary=:all:",
         "--dest", str(dependencies), "httpx>=0.28.1,<0.29", "websockets>=15.0.1,<16"], check=True,
    )
    artifacts = []
    direct = []
    derived = []
    for package in PACKAGES:
        builder = ProjectBuilder(str(package))
        direct.append(Path(builder.build("wheel", str(output / "direct"))))
        sdist = Path(builder.build("sdist", str(output / "sdist")))
        artifacts.extend((direct[-1], sdist))
        with tempfile.TemporaryDirectory(prefix="sdist-", dir=output) as temporary:
            extracted = Path(temporary)
            with tarfile.open(sdist) as archive:
                archive.extractall(extracted, filter="data")
            roots = list(extracted.iterdir())
            assert len(roots) == 1 and roots[0].is_dir()
            derived.append(
                Path(ProjectBuilder(str(roots[0])).build("wheel", str(output / "derived")))
            )
    derived = sorted((output / "derived").glob("*.whl"))
    assert len(direct) == len(derived) == 2
    artifacts.extend(derived)
    report = {
        "source_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, cwd=ROOT, capture_output=True, text=True
        ).stdout.strip(),
        "python": sys.version,
        "executable": sys.executable,
        "artifacts": {
            str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in artifacts
        },
        "dependency_wheels": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(dependencies.glob("*.whl"))
        },
        "smokes": [],
    }
    for label, wheels in (("direct", direct), ("derived", derived)):
        with tempfile.TemporaryDirectory(prefix=f"req019-{label}-", dir=output) as temporary:
            directory = Path(temporary)
            venv.EnvBuilder(with_pip=True).create(directory / "env")
            interpreter = directory / (
                "env/Scripts/python.exe" if os.name == "nt" else "env/bin/python"
            )
            subprocess.run(
                [
                    str(interpreter),
                    "-m",
                    "pip",
                    "install",
                    "--no-index",
                    "--no-deps",
                    *map(str, wheels),
                ],
                check=True,
                cwd=directory,
            )
            subprocess.run(
                [str(interpreter), "-m", "pip", "install", "--no-index",
                 "--find-links", str(dependencies), "httpx>=0.28.1,<0.29",
                 "websockets>=15.0.1,<16"],
                check=True, cwd=directory,
            )
            subprocess.run([str(interpreter), "-m", "pip", "check"], check=True,
                           cwd=directory)
            installed = subprocess.run(
                [str(interpreter), "-m", "pip", "list", "--format=json"],
                check=True, cwd=directory, capture_output=True, text=True,
            )
            smoke = subprocess.run(
                [str(interpreter), "-I", str(Path(__file__).with_name("artifact_smoke.py"))],
                check=True,
                cwd=directory,
                capture_output=True,
                text=True,
            )
            demo = subprocess.run(
                [str(interpreter), "-I", str(Path(__file__).with_name("demo_artifact_smoke.py"))],
                check=True,
                cwd=directory,
                capture_output=True,
                text=True,
            )
            for filename in ("conformance_artifact_smoke.py", "conformance_wrappers.py",
                             "ha_configuration_artifact_smoke.py", "ha_rest_artifact_smoke.py",
                             "ha_websocket_artifact_smoke.py"):
                shutil.copy2(Path(__file__).with_name(filename), directory / filename)
            conformance = []
            ha_configuration = []
            ha_rest = []
            ha_websocket = []
            for flags in (("-I",), ("-O", "-I")):
                checked = subprocess.run(
                    [str(interpreter), *flags, str(directory / "conformance_artifact_smoke.py")],
                    check=True,
                    cwd=directory,
                    capture_output=True,
                    text=True,
                )
                conformance.append(json.loads(checked.stdout))
                checked_configuration = subprocess.run(
                    [str(interpreter), *flags,
                     str(directory / "ha_configuration_artifact_smoke.py")],
                    check=True, cwd=directory, capture_output=True, text=True,
                )
                ha_configuration.append(json.loads(checked_configuration.stdout))
                checked_rest = subprocess.run(
                    [str(interpreter), *flags, str(directory / "ha_rest_artifact_smoke.py")],
                    check=True, cwd=directory, capture_output=True, text=True,
                )
                ha_rest.append(json.loads(checked_rest.stdout))
                checked_websocket = subprocess.run(
                    [str(interpreter), *flags, str(directory / "ha_websocket_artifact_smoke.py")],
                    check=True, cwd=directory, capture_output=True, text=True,
                )
                ha_websocket.append(json.loads(checked_websocket.stdout))
            report["smokes"].append(
                {
                    "pair": label,
                    **json.loads(smoke.stdout),
                    "demo": json.loads(demo.stdout),
                    "conformance": conformance,
                    "ha_configuration": ha_configuration,
                    "ha_rest": ha_rest,
                    "ha_websocket": ha_websocket,
                    "installed_distributions": json.loads(installed.stdout),
                }
            )
    (output / "provenance.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
