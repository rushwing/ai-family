"""Exercise real pytest hooks against hermetic present/absent runtime stubs."""

import json
import runpy
import subprocess
import sys
import time
from pathlib import Path

import pytest

_POPEN = subprocess.Popen
_SLEEP = time.sleep


def isolated_hooks(
    directory, *, provider_present, demo_present, conformance_present=False,
    shared_present=True, ha_configuration_present=False, ha_rest_present=False,
    httpx_present=False, ha_websocket_present=False, websockets_present=False,
    ha_health_present=False, ha_subscription_present=False, ha_normalization_present=False,
    state_store_present=False, state_events_present=False, ha_discovery_present=False,
    ha_mapping_present=False, ha_capabilities_present=False
):
    """Resolve only local stubs; never fall through to an ambient editable install."""
    root = directory / "runtime"
    if provider_present:
        package = root / "home_device_fabric"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text('"""Gate-only stub; no runtime behavior."""\n')
        if demo_present:
            for name in ("demo", "scenarios", "caller"):
                (package / (name + ".py")).write_text('"""Gate-only stub."""\n')
        if conformance_present:
            for name in ("conformance", "conformance_fixtures", "conformance_catalogue"):
                (package / (name + ".py")).write_text('"""Gate-only stub."""\n')
        if ha_configuration_present:
            (package / "ha_configuration.py").write_text('"""Gate-only stub."""\n')
        if ha_rest_present:
            (package / "ha_rest.py").write_text("import httpx\n")
        if ha_websocket_present:
            (package / "ha_websocket.py").write_text("import websockets\n")
        if ha_health_present:
            (package / "ha_health.py").write_text("import httpx\nimport websockets\n")
        if ha_subscription_present:
            (package / "ha_subscription.py").write_text("import websockets\n")
        if ha_normalization_present:
            (package / "ha_normalization.py").write_text("import state_schema.canonical_state\n")
        if ha_discovery_present:
            (package / "ha_discovery.py").write_text(
                "import websockets\nclass HARegistryDiscoveryClient:\n"
                "    async def discover(self): pass\n    async def aclose(self): pass\n")
        if ha_capabilities_present:
            (package / "ha_capabilities.py").write_text(
                "import state_schema.provider_contracts\nclass HACapabilityInferrer:\n"
                "    def infer(self): pass\n")
        if ha_mapping_present:
            (package / "ha_mapping.py").write_text(
                "import state_schema.provider_contracts\nclass HARegistryMapper:\n"
                "    def map(self): pass\n")
        if state_store_present:
            (package / "state_store.py").write_text("import state_schema.canonical_state\n")
        if state_events_present:
            (package / "state_store.py").write_text(
                "import state_schema.canonical_state\n"
                "class CurrentStateStore:\n"
                "    def apply(self): pass\n"
                "    def advance_epoch(self): pass\n")
    if httpx_present:
        root.mkdir(parents=True, exist_ok=True)
        (root / "httpx.py").write_text('"""Gate-only dependency stub."""\n')
    if shared_present:
        shared = root / "state_schema"
        shared.mkdir(parents=True)
        for name in ("__init__", "action_contracts", "canonical_state", "provider_contracts"):
            (shared / (name + ".py")).write_text('"""Gate-only stub."""\n')
    if websockets_present:
        root.mkdir(parents=True, exist_ok=True)
        (root / "websockets.py").write_text('"""Gate-only dependency stub."""\n')
    bootstrap = """import importlib.abc
import importlib.util
import sys
from pathlib import Path

class GateRuntimeFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if not any(fullname == p or fullname.startswith(p + ".")
                   for p in ("home_device_fabric", "state_schema", "httpx", "websockets")):
            return None
        stub = Path(__file__).parent / "runtime" / Path(*fullname.split("."))
        if stub.is_dir():
            return importlib.util.spec_from_file_location(fullname, stub / "__init__.py")
        if stub.with_suffix(".py").is_file():
            return importlib.util.spec_from_file_location(fullname, stub.with_suffix(".py"))
        raise ModuleNotFoundError("gate runtime intentionally absent")

for loaded_name in tuple(sys.modules):
    if any(loaded_name == p or loaded_name.startswith(p + ".")
           for p in ("home_device_fabric", "state_schema", "httpx", "websockets")):
        del sys.modules[loaded_name]
sys.meta_path.insert(0, GateRuntimeFinder())
"""
    return bootstrap + Path(__file__).with_name("conftest.py").read_text()


def run_probe(command, directory, monkeypatch):
    # Only gate subprocess I/O crosses the guard; child hooks guard runtime calls.
    with monkeypatch.context() as patch:
        patch.setattr(subprocess, "Popen", _POPEN)
        patch.setattr(time, "sleep", _SLEEP)
        try:
            # Interpreter startup and collection can exceed 30s on loaded
            # Termux hosts. Keep a finite deadline and retain timeout output.
            return subprocess.run(
                command, capture_output=True, text=True, timeout=90, cwd=directory,
            )
        except subprocess.TimeoutExpired as error:
            def output(value):
                if isinstance(value, bytes):
                    return value.decode("utf-8", errors="replace")
                return value or "<no output>"

            pytest.fail(
                f"gate probe timed out after {error.timeout}s: {command!r}\n"
                f"stdout:\n{output(error.stdout)}\nstderr:\n{output(error.stderr)}",
                pytrace=False,
            )


@pytest.mark.tc030_04
@pytest.mark.parametrize("stdout,stderr", [
    (b"partial stdout", b"partial stderr"),
    ("partial stdout", "partial stderr"),
    (None, None),
])
def test_gate_timeout_retains_diagnostics(tmp_path, monkeypatch, stdout, stderr):
    command = [sys.executable, "-I", "-m", "pytest", "test_probe.py"]

    def timeout(actual_command, **kwargs):
        assert actual_command == command
        assert kwargs == {"capture_output": True, "text": True, "timeout": 90, "cwd": tmp_path}
        raise subprocess.TimeoutExpired(command, 90, output=stdout, stderr=stderr)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(pytest.fail.Exception) as caught:
        run_probe(command, tmp_path, monkeypatch)
    message = str(caught.value)
    assert "gate probe timed out after 90s" in message
    assert "test_probe.py" in message
    assert "stdout:\n" in message and "stderr:\n" in message
    if stdout is None:
        assert message.count("<no output>") == 2
    else:
        assert "partial stdout" in message and "partial stderr" in message


@pytest.mark.parametrize("flag", ["provider", "demo", "conformance"])
@pytest.mark.parametrize(
    "missing,required,exitcode", [(True, False, 0), (True, True, 4), (False, True, 1)]
)
@pytest.mark.tc019_06
def test_required_runtime_gate(tmp_path, monkeypatch, missing, required, exitcode, flag):
    hooks = isolated_hooks(
        tmp_path,
        provider_present=not (missing and flag == "provider"),
        demo_present=not (missing and flag == "demo"),
        conformance_present=not (missing and flag == "conformance"),
    )
    (tmp_path / "conftest.py").write_text(hooks)
    (
        tmp_path
        / (
            "test_demo.py"
            if flag == "demo"
            else "test_conformance.py"
            if flag == "conformance"
            else "test_probe.py"
        )
    ).write_text(
        "import pytest\n"
        + (
            "def test_probe(): pass\n"
            if missing
            else "@pytest.mark.skip(reason='explicit acceptance probe')\ndef test_probe(): pass\n"
        )
    )
    command = [
        sys.executable,
        "-I",
        "-m",
        "pytest",
        str(tmp_path),
        "-q",
        "--confcutdir",
        str(tmp_path),
    ]
    if required:
        command.append("--require-" + flag + "-runtime")
    result = run_probe(command, tmp_path, monkeypatch)
    assert result.returncode == exitcode, result.stdout + result.stderr
    if missing and required:
        assert flag + " runtime required but absent" in result.stderr
    else:
        assert "1 skipped" in result.stdout


@pytest.mark.parametrize("provider_present", [True, False])
@pytest.mark.tc019_06
def test_gate_probes_execute_without_demo_or_provider(tmp_path, monkeypatch, provider_present):
    # Test the actual gate tests in a test-first layout, and with the entire runtime
    # absent. Required acceptance still fails absence; only gate probes are exempt
    # from optional-mode missing-runtime skips.
    (tmp_path / "conftest.py").write_text(
        isolated_hooks(tmp_path, provider_present=provider_present, demo_present=False)
    )
    (tmp_path / "test_gate.py").write_text(Path(__file__).read_text())
    result = run_probe(
        [
            sys.executable,
            "-I",
            "-m",
            "pytest",
            str(tmp_path),
            "-q",
            "--confcutdir",
            str(tmp_path),
            "-k",
            "test_required_runtime_gate",
        ],
        tmp_path,
        monkeypatch,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "9 passed" in result.stdout and "skipped" not in result.stdout


@pytest.mark.tc021_06
@pytest.mark.parametrize("missing", ["shared", "provider", "conformance"])
def test_conformance_required_rejects_each_missing_component(tmp_path, monkeypatch, missing):
    (tmp_path / "conftest.py").write_text(
        isolated_hooks(
            tmp_path,
            provider_present=missing != "provider",
            demo_present=True,
            conformance_present=missing != "conformance",
            shared_present=missing != "shared",
        )
    )
    (tmp_path / "test_conformance.py").write_text("def test_probe(): pass\n")
    result = run_probe(
        [
            sys.executable,
            "-I",
            "-m",
            "pytest",
            str(tmp_path),
            "-q",
            "--confcutdir",
            str(tmp_path),
            "--require-conformance-runtime",
        ],
        tmp_path,
        monkeypatch,
    )
    assert result.returncode == 4
    assert "conformance runtime required but absent" in result.stderr


@pytest.mark.tc022_06
@pytest.mark.parametrize("provider,module,shared,required,skip,expected", [
    (False, False, True, True, False, 4),
    (True, False, True, True, False, 4),
    (True, True, False, True, False, 4),
    (True, False, True, False, False, 0),
    (True, True, True, True, True, 1),
    (True, True, True, True, False, 0),
])
def test_ha_configuration_required_gate(tmp_path, monkeypatch, provider, module,
                                        shared, required, skip, expected):
    (tmp_path / "conftest.py").write_text(isolated_hooks(
        tmp_path, provider_present=provider, demo_present=False,
        ha_configuration_present=module, shared_present=shared))
    text = "import pytest\n"
    if skip:
        text += "@pytest.mark.skip(reason='mandatory skip probe')\n"
    text += "def test_probe(): pass\n"
    (tmp_path / "test_ha_configuration.py").write_text(text)
    command = [sys.executable, "-I", "-m", "pytest", str(tmp_path), "-q",
               "--confcutdir", str(tmp_path)]
    if required:
        command.append("--require-ha-configuration-runtime")
    result = run_probe(command, tmp_path, monkeypatch)
    assert result.returncode == expected, result.stdout + result.stderr
    if expected == 4:
        assert "ha-configuration runtime required but absent" in result.stderr
    elif skip or not module:
        assert "1 skipped" in result.stdout
    else:
        assert "1 passed" in result.stdout


@pytest.mark.tc023_06
@pytest.mark.parametrize("provider,module,dependency,required,skip,expected", [
    (False, False, False, True, False, 4),
    (True, False, True, True, False, 4),
    (True, True, False, True, False, 4),
    (True, False, True, False, False, 0),
    (True, True, True, True, True, 1),
    (True, True, True, True, False, 0),
])
def test_ha_rest_required_gate(tmp_path, monkeypatch, provider, module, dependency,
                               required, skip, expected):
    (tmp_path / "conftest.py").write_text(isolated_hooks(
        tmp_path, provider_present=provider, demo_present=False,
        ha_rest_present=module, httpx_present=dependency))
    text = "import pytest\n"
    if skip:
        text += "@pytest.mark.skip(reason='mandatory skip probe')\n"
    text += "def test_probe(): pass\n"
    (tmp_path / "test_ha_rest.py").write_text(text)
    command = [sys.executable, "-I", "-m", "pytest", str(tmp_path), "-q",
               "--confcutdir", str(tmp_path)]
    if required:
        command.append("--require-ha-rest-runtime")
    result = run_probe(command, tmp_path, monkeypatch)
    assert result.returncode == expected, result.stdout + result.stderr
    if expected == 4:
        assert "ha-rest runtime required but absent" in result.stderr
    elif skip or not module:
        assert "1 skipped" in result.stdout
    else:
        assert "1 passed" in result.stdout


@pytest.mark.tc024_06
@pytest.mark.parametrize("provider,module,dependency,required,skip,expected", [
    (False, False, False, True, False, 4),
    (True, False, True, True, False, 4),
    (True, True, False, True, False, 4),
    (True, False, True, False, False, 0),
    (True, True, True, True, True, 1),
    (True, True, True, True, False, 0),
    (True, True, False, False, False, 0),
    (True, "broken", True, True, False, 4),
    (True, "broken", True, False, False, 0),
    (True, "broken-attribute", True, True, False, 4),
    (True, "broken-attribute", True, False, False, 0),
])
def test_ha_websocket_required_gate(tmp_path, monkeypatch, provider, module, dependency,
                                    required, skip, expected):
    (tmp_path / "conftest.py").write_text(isolated_hooks(
        tmp_path, provider_present=provider, demo_present=False,
        ha_websocket_present=module, websockets_present=dependency))
    exception_type = {"broken": "RuntimeError", "broken-attribute": "AttributeError"}.get(module)
    if exception_type:
        (tmp_path / "runtime/home_device_fabric/ha_websocket.py").write_text(
            f"raise {exception_type}('controlled import failure')\n")
    text = "import pytest\n"
    if skip:
        text += "@pytest.mark.skip(reason='mandatory skip probe')\n"
    text += "def test_probe(): pass\n"
    (tmp_path / "test_ha_websocket.py").write_text(text)
    command = [sys.executable, "-I", "-m", "pytest", str(tmp_path), "-q", "-rs",
               "--confcutdir", str(tmp_path)]
    if required:
        command.append("--require-ha-websocket-runtime")
    result = run_probe(command, tmp_path, monkeypatch)
    assert result.returncode == expected, result.stdout + result.stderr
    diagnosis = "broken" if exception_type else "absent"
    assert "controlled import failure" not in result.stdout + result.stderr
    if expected == 4:
        assert "ha-websocket runtime required but " + diagnosis in result.stderr
    elif skip or not module or not dependency or exception_type:
        assert "1 skipped" in result.stdout
        if not skip:
            assert "ha-websocket runtime " + diagnosis in result.stdout
    else:
        assert "1 passed" in result.stdout


@pytest.mark.tc024_06
@pytest.mark.tc032_04
@pytest.mark.tc033_04
def test_ci_requires_complete_fabric_acceptance():
    root = Path(__file__).resolve().parents[4]
    validate = runpy.run_path(str(root / "tools/check_fabric_ci.py"))["validate"]
    workflow = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert validate(workflow) == []
    for flag in ("--require-provider-runtime", "--require-demo-runtime",
                 "--require-conformance-runtime", "--require-ha-configuration-runtime",
                 "--require-ha-rest-runtime", "--require-ha-websocket-runtime",
                 "--require-ha-health-runtime", "--require-ha-subscription-runtime",
                 "--require-ha-normalization-runtime", "--require-state-store-runtime",
                 "--require-state-events-runtime", "--require-ha-discovery-runtime",
                 "--require-ha-mapping-runtime", "--require-ha-capabilities-runtime"):
        assert validate(workflow.replace(flag, "")) == ["missing fabric acceptance flag: " + flag]
    assert validate(workflow.replace("python -m pytest", "echo python -m pytest"))
    assert validate(workflow.replace("home-device-fabric-tc:", "disabled-fabric:"))


@pytest.mark.tc026_05
@pytest.mark.parametrize("module,dependency,required,skip,expected", [
    (False, True, True, False, 4), (True, False, True, False, 4),
    ("broken", True, True, False, 4), ("broken", True, False, False, 0),
    (False, True, False, False, 0), (True, True, True, True, 1),
    (True, True, True, False, 0),
])
def test_ha_health_required_gate(tmp_path, monkeypatch, module, dependency,
                                 required, skip, expected):
    (tmp_path / "conftest.py").write_text(isolated_hooks(
        tmp_path, provider_present=True, demo_present=False, ha_health_present=module,
        httpx_present=dependency, websockets_present=dependency))
    if module == "broken":
        (tmp_path / "runtime/home_device_fabric/ha_health.py").write_text(
            "raise AttributeError('private import details')\n")
    text = "import pytest\n"
    if skip:
        text += "@pytest.mark.skip(reason='mandatory skip probe')\n"
    text += "def test_probe(): pass\n"
    # Required mode must diagnose missing runtime even under unrelated selection.
    filename = "test_probe.py" if required and expected == 4 else "test_ha_health.py"
    (tmp_path / filename).write_text(text)
    command = [sys.executable, "-I", "-m", "pytest", str(tmp_path), "-q", "-rs",
               "--confcutdir", str(tmp_path)]
    if required:
        command.append("--require-ha-health-runtime")
    result = run_probe(command, tmp_path, monkeypatch)
    assert result.returncode == expected, result.stdout + result.stderr
    assert "private import details" not in result.stdout + result.stderr
    if expected == 4:
        diagnosis = "broken" if module == "broken" else "absent"
        assert "ha-health runtime required but " + diagnosis in result.stderr
    elif skip or not module or module == "broken":
        assert "1 skipped" in result.stdout
    else:
        assert "1 passed" in result.stdout


@pytest.mark.tc027_05
@pytest.mark.parametrize("module,dependency,required,skip,expected", [
    (False, True, True, False, 4), (True, False, True, False, 4),
    ("broken", True, True, False, 4), ("broken", True, False, False, 0),
    (False, True, False, False, 0), (True, True, True, True, 1),
    (True, True, True, False, 0),
])
def test_ha_subscription_required_gate(tmp_path, monkeypatch, module, dependency,
                                 required, skip, expected):
    (tmp_path / "conftest.py").write_text(isolated_hooks(
        tmp_path, provider_present=True, demo_present=False, ha_subscription_present=module,
        httpx_present=dependency, websockets_present=dependency))
    if module == "broken":
        (tmp_path / "runtime/home_device_fabric/ha_subscription.py").write_text(
            "raise AttributeError('private import details')\n")
    text = "import pytest\n"
    if skip:
        text += "@pytest.mark.skip(reason='mandatory skip probe')\n"
    text += "def test_probe(): pass\n"
    # Required mode must diagnose missing runtime even under unrelated selection.
    filename = "test_probe.py" if required and expected == 4 else "test_ha_subscription.py"
    (tmp_path / filename).write_text(text)
    command = [sys.executable, "-I", "-m", "pytest", str(tmp_path), "-q", "-rs",
               "--confcutdir", str(tmp_path)]
    if required:
        command.append("--require-ha-subscription-runtime")
    result = run_probe(command, tmp_path, monkeypatch)
    assert result.returncode == expected, result.stdout + result.stderr
    assert "private import details" not in result.stdout + result.stderr
    if expected == 4:
        diagnosis = "broken" if module == "broken" else "absent"
        assert "ha-subscription runtime required but " + diagnosis in result.stderr
    elif skip or not module or module == "broken":
        assert "1 skipped" in result.stdout
    else:
        assert "1 passed" in result.stdout


@pytest.mark.tc028_04
@pytest.mark.parametrize("module,dependency,required,skip,expected", [
    (False, True, True, False, 4), (True, False, True, False, 4),
    ("broken", True, True, False, 4), ("broken", True, False, False, 0),
    (False, True, False, False, 0), (True, True, True, True, 1),
    (True, True, True, False, 0),
])
def test_ha_normalization_required_gate(tmp_path, monkeypatch, module, dependency,
                                 required, skip, expected):
    (tmp_path / "conftest.py").write_text(isolated_hooks(
        tmp_path, provider_present=True, demo_present=False, ha_normalization_present=module,
        shared_present=dependency))
    if module == "broken":
        (tmp_path / "runtime/home_device_fabric/ha_normalization.py").write_text(
            "raise AttributeError('private import details')\n")
    text = "import pytest\n"
    if skip:
        text += "@pytest.mark.skip(reason='mandatory skip probe')\n"
    text += "def test_probe(): pass\n"
    # Required mode must diagnose missing runtime even under unrelated selection.
    filename = "test_probe.py" if required and expected == 4 else "test_ha_normalization.py"
    (tmp_path / filename).write_text(text)
    command = [sys.executable, "-I", "-m", "pytest", str(tmp_path), "-q", "-rs",
               "--confcutdir", str(tmp_path)]
    if required:
        command.append("--require-ha-normalization-runtime")
    result = run_probe(command, tmp_path, monkeypatch)
    assert result.returncode == expected, result.stdout + result.stderr
    assert "private import details" not in result.stdout + result.stderr
    if expected == 4:
        diagnosis = "broken" if module == "broken" else "absent"
        assert "ha-normalization runtime required but " + diagnosis in result.stderr
    elif skip or not module or module == "broken":
        assert "1 skipped" in result.stdout
    else:
        assert "1 passed" in result.stdout


@pytest.mark.tc029_04
@pytest.mark.parametrize("module,dependency,required,skip,expected", [
    (False, True, True, False, 4), (True, False, True, False, 4),
    ("broken", True, True, False, 4), ("broken", True, False, False, 0),
    (False, True, False, False, 0), (True, True, True, True, 1),
    (True, True, True, False, 0),
])
def test_state_store_required_gate(tmp_path, monkeypatch, module, dependency,
                                 required, skip, expected):
    (tmp_path / "conftest.py").write_text(isolated_hooks(
        tmp_path, provider_present=True, demo_present=False, state_store_present=module,
        shared_present=dependency))
    if module == "broken":
        (tmp_path / "runtime/home_device_fabric/state_store.py").write_text(
            "raise AttributeError('private import details')\n")
    text = "import pytest\n"
    if skip:
        text += "@pytest.mark.skip(reason='mandatory skip probe')\n"
    text += "def test_probe(): pass\n"
    # Required mode must diagnose missing runtime even under unrelated selection.
    filename = "test_probe.py" if required and expected == 4 else "test_state_store.py"
    (tmp_path / filename).write_text(text)
    command = [sys.executable, "-I", "-m", "pytest", str(tmp_path), "-q", "-rs",
               "--confcutdir", str(tmp_path)]
    if required:
        command.append("--require-state-store-runtime")
    result = run_probe(command, tmp_path, monkeypatch)
    assert result.returncode == expected, result.stdout + result.stderr
    assert "private import details" not in result.stdout + result.stderr
    if expected == 4:
        diagnosis = "broken" if module == "broken" else "absent"
        assert "state-store runtime required but " + diagnosis in result.stderr
    elif skip or not module or module == "broken":
        assert "1 skipped" in result.stdout
    else:
        assert "1 passed" in result.stdout


@pytest.mark.tc030_04
@pytest.mark.parametrize("module,required,skip,expected", [
    (False, True, False, 4), ("broken", True, False, 4),
    ("methods_missing", True, False, 4), ("dependency_missing", True, False, 4),
    ("broken", False, False, 0), (False, False, False, 0),
    ("methods_missing", False, False, 0), (True, True, True, 1),
    (True, True, False, 0),
])
def test_state_events_required_gate(tmp_path, monkeypatch, module, required, skip, expected):
    (tmp_path / "conftest.py").write_text(isolated_hooks(
        tmp_path, provider_present=True, demo_present=False,
        state_events_present=bool(module), shared_present=module != "dependency_missing"))
    path = tmp_path / "runtime/home_device_fabric/state_store.py"
    if module == "broken":
        path.write_text("raise AttributeError('private import details')\n")
    elif module == "methods_missing":
        path.write_text("class CurrentStateStore: pass\n")
    text = "import pytest\n"
    if skip:
        text += "@pytest.mark.skip(reason='mandatory skip probe')\n"
    text += "def test_probe(): pass\n"
    filename = "test_probe.py" if required and expected == 4 else "test_state_events.py"
    (tmp_path / filename).write_text(text)
    command = [sys.executable, "-I", "-m", "pytest", str(tmp_path), "-q", "-rs",
               "--confcutdir", str(tmp_path)]
    if required:
        command.append("--require-state-events-runtime")
    result = run_probe(command, tmp_path, monkeypatch)
    assert result.returncode == expected, result.stdout + result.stderr
    assert "private import details" not in result.stdout + result.stderr
    if expected == 4:
        diagnosis = "broken" if module == "broken" else "absent"
        assert "state-events runtime required but " + diagnosis in result.stderr
    elif skip or module in (False, "broken", "methods_missing"):
        assert "1 skipped" in result.stdout
    else:
        assert "1 passed" in result.stdout


@pytest.mark.tc031_04
@pytest.mark.parametrize("module,required,skip,expected", [
    (False, True, False, 4), ("broken", True, False, 4),
    ("methods_missing", True, False, 4), ("dependency_missing", True, False, 4),
    ("broken", False, False, 0), (False, False, False, 0),
    ("methods_missing", False, False, 0), ("dependency_missing", False, False, 0),
    (True, True, True, 1), (True, True, False, 0),
])
def test_ha_discovery_required_gate(tmp_path, monkeypatch, module, required, skip, expected):
    (tmp_path / "conftest.py").write_text(isolated_hooks(
        tmp_path, provider_present=True, demo_present=False,
        ha_discovery_present=bool(module), websockets_present=module != "dependency_missing"))
    path = tmp_path / "runtime/home_device_fabric/ha_discovery.py"
    if module == "broken":
        path.write_text("raise AttributeError('private import details')\n")
    elif module == "methods_missing":
        path.write_text("class HARegistryDiscoveryClient: pass\n")
    text = "import pytest\n"
    if skip:
        text += "@pytest.mark.skip(reason='mandatory skip probe')\n"
    text += "def test_probe(): pass\n"
    filename = "test_probe.py" if required and expected == 4 else "test_ha_discovery.py"
    (tmp_path / filename).write_text(text)
    command = [sys.executable, "-I", "-m", "pytest", str(tmp_path), "-q", "-rs",
               "--confcutdir", str(tmp_path)]
    if required:
        command.append("--require-ha-discovery-runtime")
    result = run_probe(command, tmp_path, monkeypatch)
    assert result.returncode == expected, result.stdout + result.stderr
    assert "private import details" not in result.stdout + result.stderr
    if expected == 4:
        diagnosis = "broken" if module == "broken" else "absent"
        assert "ha-discovery runtime required but " + diagnosis in result.stderr
    elif skip or module in (False, "broken", "methods_missing", "dependency_missing"):
        assert "1 skipped" in result.stdout
    else:
        assert "1 passed" in result.stdout


@pytest.mark.tc032_04
@pytest.mark.parametrize("module,required,skip,expected", [
    (False, True, False, 4), ("broken", True, False, 4),
    ("methods_missing", True, False, 4), ("dependency_missing", True, False, 4),
    ("broken", False, False, 0), (False, False, False, 0),
    ("methods_missing", False, False, 0), ("dependency_missing", False, False, 0),
    (True, True, True, 1), (True, True, False, 0),
])
def test_ha_mapping_required_gate(tmp_path, monkeypatch, module, required, skip, expected):
    (tmp_path / "conftest.py").write_text(isolated_hooks(
        tmp_path, provider_present=True, demo_present=False,
        ha_mapping_present=bool(module), shared_present=module != "dependency_missing"))
    path = tmp_path / "runtime/home_device_fabric/ha_mapping.py"
    if module == "broken":
        path.write_text("raise AttributeError('private import details')\n")
    elif module == "methods_missing":
        path.write_text("class HARegistryMapper: pass\n")
    text = "import pytest\n"
    if skip:
        text += "@pytest.mark.skip(reason='mandatory skip probe')\n"
    text += "def test_probe(): pass\n"
    filename = "test_probe.py" if required and expected == 4 else "test_ha_mapping.py"
    (tmp_path / filename).write_text(text)
    command = [sys.executable, "-I", "-m", "pytest", str(tmp_path), "-q", "-rs",
               "--confcutdir", str(tmp_path)]
    if required:
        command.append("--require-ha-mapping-runtime")
    actual_tests = module is False or module == "broken" or module == "dependency_missing"
    if actual_tests:
        # A top-level runtime import would fail collection before the gate could
        # classify absence or apply optional skips. Exercise the real test module.
        (tmp_path / filename).unlink()
        (tmp_path / "test_ha_mapping.py").write_text(
            Path(__file__).with_name("test_ha_mapping.py").read_text())
    result = run_probe(command, tmp_path, monkeypatch)
    assert result.returncode == expected, result.stdout + result.stderr
    assert "private import details" not in result.stdout + result.stderr
    if expected == 4:
        diagnosis = "broken" if module == "broken" else "absent"
        assert "ha-mapping runtime required but " + diagnosis in result.stderr
    elif skip or module in (False, "broken", "methods_missing", "dependency_missing"):
        assert ("121 skipped" if actual_tests else "1 skipped") in result.stdout
    else:
        assert "1 passed" in result.stdout


@pytest.mark.tc032_04
@pytest.mark.parametrize("optimized", [False, True])
def test_installed_smoke_logic_in_isolated_python(tmp_path, monkeypatch, optimized):
    import sys
    from pathlib import Path

    command = [sys.executable, "-I"]
    if optimized:
        command.append("-O")
    command.append(str(Path(__file__).with_name("ha_mapping_artifact_smoke.py")))
    result = run_probe(command, tmp_path, monkeypatch)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == {"checks": 16, "offline": True, "rules_version": 1}


@pytest.mark.tc033_04
@pytest.mark.parametrize("module,required,skip,expected", [
    (False, True, False, 4), ("broken", True, False, 4),
    ("methods_missing", True, False, 4), ("dependency_missing", True, False, 4),
    ("broken", False, False, 0), (False, False, False, 0),
    ("methods_missing", False, False, 0), ("dependency_missing", False, False, 0),
    (True, True, True, 1), (True, True, False, 0),
])
def test_ha_capabilities_required_gate(tmp_path, monkeypatch, module, required, skip, expected):
    (tmp_path / "conftest.py").write_text(isolated_hooks(
        tmp_path, provider_present=True, demo_present=False,
        ha_capabilities_present=bool(module), shared_present=module != "dependency_missing"))
    path = tmp_path / "runtime/home_device_fabric/ha_capabilities.py"
    if module == "broken":
        path.write_text("raise AttributeError('private import details')\n")
    elif module == "methods_missing":
        path.write_text("class HACapabilityInferrer: pass\n")
    text = "import pytest\n"
    if skip:
        text += "@pytest.mark.skip(reason='mandatory skip probe')\n"
    text += "def test_probe(): pass\n"
    filename = "test_probe.py" if required and expected == 4 else "test_ha_capabilities.py"
    (tmp_path / filename).write_text(text)
    command = [sys.executable, "-I", "-m", "pytest", str(tmp_path), "-q", "-rs",
               "--confcutdir", str(tmp_path)]
    if required:
        command.append("--require-ha-capabilities-runtime")
    actual_tests = module is False or module == "broken" or module == "dependency_missing"
    if actual_tests:
        # A top-level runtime import would fail collection before the gate could
        # classify absence or apply optional skips. Exercise the real test module.
        (tmp_path / filename).unlink()
        (tmp_path / "test_ha_capabilities.py").write_text(
            Path(__file__).with_name("test_ha_capabilities.py").read_text())
    result = run_probe(command, tmp_path, monkeypatch)
    assert result.returncode == expected, result.stdout + result.stderr
    assert "private import details" not in result.stdout + result.stderr
    if expected == 4:
        diagnosis = "broken" if module == "broken" else "absent"
        assert "ha-capabilities runtime required but " + diagnosis in result.stderr
    elif skip or module in (False, "broken", "methods_missing", "dependency_missing"):
        assert ("127 skipped" if actual_tests else "1 skipped") in result.stdout
    else:
        assert "1 passed" in result.stdout



@pytest.mark.tc033_04
@pytest.mark.parametrize("optimized", [False, True])
def test_capabilities_smoke_logic_in_isolated_python(tmp_path, monkeypatch, optimized):
    import sys
    from pathlib import Path

    command = [sys.executable, "-I"]
    if optimized:
        command.append("-O")
    command.append(str(Path(__file__).with_name("ha_capabilities_artifact_smoke.py")))
    result = run_probe(command, tmp_path, monkeypatch)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == {"checks": 16, "offline": True, "rules_version": 1}
