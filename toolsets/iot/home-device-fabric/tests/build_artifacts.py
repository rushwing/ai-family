"""Build both distributions and verify isolated direct/sdist-derived wheel pairs.

Run in an environment with build, hatchling and pip installed. Builds use no
isolation. Resolve HTTPX's dependency wheels once, then install each compatible
package pair and that recorded closure offline into fresh smoke environments.
"""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import venv
from pathlib import Path

from artifact_provenance import (
    INDEX_URL,
    dependency_download_environment,
    summarize_test_results,
    verify_dependency_wheels,
)
from build import ProjectBuilder

ROOT = Path(__file__).resolve().parents[4]
PACKAGES = (ROOT / "libs/state-schema", ROOT / "toolsets/iot/home-device-fabric")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--test-results", type=Path, action="append", default=[])
    parser.add_argument("--expected-test-count", type=int, action="append", default=[])
    args = parser.parse_args()
    test_results = summarize_test_results(args.test_results, args.expected_test_count)
    output = args.out_dir.resolve()
    assert not output.is_relative_to(ROOT), "Artifacts and smoke must run outside the checkout"
    output.mkdir(parents=True, exist_ok=True)
    dependencies = output / "dependencies"
    # A fresh wheelhouse avoids silently reusing stale/mirror-supplied bytes.
    dependencies.mkdir()
    download_env = dependency_download_environment(os.environ)
    download = subprocess.run(
        [sys.executable, "-m", "pip", "download", "--only-binary=:all:",
         "--index-url", INDEX_URL, "--no-cache-dir", "--disable-pip-version-check",
         "--dest", str(dependencies), "httpx>=0.28.1,<0.29", "websockets>=15.0.1,<16",
         "certifi>=2024.8.30,<2027"], check=True, env=download_env,
        capture_output=True,
    )
    verified_dependencies = verify_dependency_wheels(dependencies)
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
        "platform": platform.platform(),
        "machine": platform.machine(),
        "system": platform.system(),
        "implementation": platform.python_implementation(),
        "test_results": test_results,
        "runtime_sha256": hashlib.sha256((PACKAGES[1] /
            "src/home_device_fabric/ha_websocket.py").read_bytes()).hexdigest(),
        "health_runtime_sha256": hashlib.sha256((PACKAGES[1] /
            "src/home_device_fabric/ha_health.py").read_bytes()).hexdigest(),
        "normalization_runtime_sha256": hashlib.sha256((PACKAGES[1] /
            "src/home_device_fabric/ha_normalization.py").read_bytes()).hexdigest(),
        "mapping_runtime_sha256": hashlib.sha256((PACKAGES[1] /
            "src/home_device_fabric/ha_mapping.py").read_bytes()).hexdigest(),
        "discovery_runtime_sha256": hashlib.sha256((PACKAGES[1] /
            "src/home_device_fabric/ha_discovery.py").read_bytes()).hexdigest(),
        "state_events_runtime_sha256": hashlib.sha256((PACKAGES[1] /
            "src/home_device_fabric/state_store.py").read_bytes()).hexdigest(),
        "state_store_runtime_sha256": hashlib.sha256((PACKAGES[1] /
            "src/home_device_fabric/state_store.py").read_bytes()).hexdigest(),
        "subscription_runtime_sha256": hashlib.sha256((PACKAGES[1] /
            "src/home_device_fabric/ha_subscription.py").read_bytes()).hexdigest(),
        "source_dirty": bool(subprocess.run(
            ["git", "status", "--porcelain"], check=True, cwd=ROOT,
            capture_output=True, text=True).stdout.strip()),
        "dependency_verification": verified_dependencies,
        "dependency_acquisition": {
            "index_url": INDEX_URL, "pip_version": importlib.metadata.version("pip"),
            "pip_config_file": os.devnull, "cache": "disabled",
            "ignored_pip_environment_keys": sorted(k for k in os.environ
                                                   if k.upper().startswith("PIP_")),
            "proxy_policy": "disabled for pip downloads and release metadata",
            "ignored_proxy_environment_keys": sorted(
                k for k in os.environ if k.upper().endswith("_PROXY")),
            "download_stdout_sha256": hashlib.sha256(download.stdout).hexdigest(),
            "download_stderr_sha256": hashlib.sha256(download.stderr).hexdigest(),
            "download_returncode": download.returncode,
            "log_policy": "Raw pip output and environment values are not exported; "
                          "verified file URLs and identities form the acquisition log.",
        },
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
                 "websockets>=15.0.1,<16", "certifi>=2024.8.30,<2027"],
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
                             "ha_websocket_artifact_smoke.py", "ha_health_artifact_smoke.py",
                             "ha_subscription_artifact_smoke.py",
                             "ha_normalization_artifact_smoke.py", "state_store_artifact_smoke.py",
                             "state_events_artifact_smoke.py",
                             "state_application_artifact_smoke.py",
                             "ha_discovery_artifact_smoke.py", "ha_mapping_artifact_smoke.py"):
                shutil.copy2(Path(__file__).with_name(filename), directory / filename)
            conformance = []
            ha_configuration = []
            ha_rest = []
            ha_websocket = []
            ha_health = []
            ha_subscription = []
            ha_normalization = []
            state_store = []
            state_application = []
            state_events = []
            ha_discovery = []
            ha_mapping = []
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
                checked_health = subprocess.run(
                    [str(interpreter), *flags, str(directory / "ha_health_artifact_smoke.py")],
                    check=True, cwd=directory, capture_output=True, text=True,
                )
                ha_health.append(json.loads(checked_health.stdout))
                checked_subscription = subprocess.run(
                    [str(interpreter), *flags,
                     str(directory / "ha_subscription_artifact_smoke.py")],
                    check=True, cwd=directory, capture_output=True, text=True,
                )
                ha_subscription.append(json.loads(checked_subscription.stdout))
                checked_normalization = subprocess.run(
                    [str(interpreter), *flags,
                     str(directory / "ha_normalization_artifact_smoke.py")],
                    check=True, cwd=directory, capture_output=True, text=True,
                )
                ha_normalization.append(json.loads(checked_normalization.stdout))
                checked_store = subprocess.run(
                    [str(interpreter), *flags, str(directory / "state_store_artifact_smoke.py")],
                    check=True, cwd=directory, capture_output=True, text=True,
                )
                state_store.append(json.loads(checked_store.stdout))
                checked_application = subprocess.run(
                    [str(interpreter), *flags,
                     str(directory / "state_application_artifact_smoke.py")],
                    check=True, cwd=directory, capture_output=True, text=True,
                )
                state_application.append(json.loads(checked_application.stdout))
                checked_events = subprocess.run(
                    [str(interpreter), *flags, str(directory / "state_events_artifact_smoke.py")],
                    check=True, cwd=directory, capture_output=True, text=True,
                )
                state_events.append(json.loads(checked_events.stdout))
                checked_discovery = subprocess.run(
                    [str(interpreter), *flags, str(directory / "ha_discovery_artifact_smoke.py")],
                    check=True, cwd=directory, capture_output=True, text=True,
                )
                ha_discovery.append(json.loads(checked_discovery.stdout))
                checked_mapping = subprocess.run(
                    [str(interpreter), *flags, str(directory / "ha_mapping_artifact_smoke.py")],
                    check=True, cwd=directory, capture_output=True, text=True,
                )
                ha_mapping.append(json.loads(checked_mapping.stdout))
            report["smokes"].append(
                {
                    "pair": label,
                    **json.loads(smoke.stdout),
                    "demo": json.loads(demo.stdout),
                    "conformance": conformance,
                    "ha_configuration": ha_configuration,
                    "ha_rest": ha_rest,
                    "ha_websocket": ha_websocket,
                    "ha_health": ha_health,
                    "ha_subscription": ha_subscription,
                    "ha_normalization": ha_normalization,
                    "state_store": state_store,
                    "state_application": state_application,
                    "state_events": state_events,
                    "ha_discovery": ha_discovery,
                    "ha_mapping": ha_mapping,
                    "installed_distributions": json.loads(installed.stdout),
                }
            )
    (output / "provenance.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
