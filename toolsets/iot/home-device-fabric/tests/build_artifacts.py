"""Build both distributions and verify isolated direct/sdist-derived wheel pairs.

Run in an environment with build and hatchling installed. Builds use no isolation
or dependency downloads; installed smoke environments contain only the two wheels.
"""

import argparse
import hashlib
import json
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
            derived.append(Path(ProjectBuilder(str(roots[0])).build(
                "wheel", str(output / "derived")
            )))
    derived = sorted((output / "derived").glob("*.whl"))
    assert len(direct) == len(derived) == 2
    artifacts.extend(derived)
    report = {
        "python": sys.version,
        "executable": sys.executable,
        "artifacts": {str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in artifacts},
        "smokes": [],
    }
    for label, wheels in (("direct", direct), ("derived", derived)):
        with tempfile.TemporaryDirectory(prefix=f"req019-{label}-", dir=output) as temporary:
            directory = Path(temporary)
            venv.EnvBuilder(with_pip=True).create(directory / "env")
            interpreter = directory / "env/bin/python"
            subprocess.run(
                [str(interpreter), "-m", "pip", "install", "--no-index", "--no-deps",
                 *map(str, wheels)], check=True, cwd=directory,
            )
            smoke = subprocess.run(
                [str(interpreter), "-I", str(Path(__file__).with_name("artifact_smoke.py"))],
                check=True, cwd=directory, capture_output=True, text=True,
            )
            report["smokes"].append({"pair": label, **json.loads(smoke.stdout)})
    (output / "provenance.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
