"""Exercise real pytest hooks against hermetic present/absent runtime stubs."""

import subprocess
import sys
import time
from pathlib import Path

import pytest

_POPEN = subprocess.Popen
_SLEEP = time.sleep


def isolated_hooks(directory, *, provider_present, demo_present):
    """Resolve only local stubs; never fall through to an ambient editable install."""
    root = directory / "runtime"
    if provider_present:
        package = root / "home_device_fabric"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text('"""Gate-only stub; no runtime behavior."""\n')
        if demo_present:
            for name in ("demo", "scenarios", "caller"):
                (package / (name + ".py")).write_text('"""Gate-only stub."""\n')
    bootstrap = '''import importlib.abc
import importlib.util
import sys
from pathlib import Path

class GateRuntimeFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname != "home_device_fabric" and not fullname.startswith("home_device_fabric."):
            return None
        stub = Path(__file__).parent / "runtime" / Path(*fullname.split("."))
        if stub.is_dir():
            return importlib.util.spec_from_file_location(fullname, stub / "__init__.py")
        if stub.with_suffix(".py").is_file():
            return importlib.util.spec_from_file_location(fullname, stub.with_suffix(".py"))
        raise ModuleNotFoundError("gate runtime intentionally absent")

for loaded_name in tuple(sys.modules):
    if loaded_name == "home_device_fabric" or loaded_name.startswith("home_device_fabric."):
        del sys.modules[loaded_name]
sys.meta_path.insert(0, GateRuntimeFinder())
'''
    return bootstrap + Path(__file__).with_name("conftest.py").read_text()


def run_probe(command, directory, monkeypatch):
    # Only gate subprocess I/O crosses the guard; child hooks guard runtime calls.
    with monkeypatch.context() as patch:
        patch.setattr(subprocess, "Popen", _POPEN)
        patch.setattr(time, "sleep", _SLEEP)
        return subprocess.run(command, capture_output=True, text=True, timeout=30, cwd=directory)


@pytest.mark.parametrize("flag", ["provider", "demo"])
@pytest.mark.parametrize("missing,required,exitcode", [(True, False, 0), (True, True, 4),
                                                      (False, True, 1)])
@pytest.mark.tc019_06
def test_required_runtime_gate(tmp_path, monkeypatch, missing, required, exitcode, flag):
    hooks = isolated_hooks(tmp_path, provider_present=not (missing and flag == "provider"),
                           demo_present=not (missing and flag == "demo"))
    (tmp_path / "conftest.py").write_text(hooks)
    (tmp_path / ("test_demo.py" if flag == "demo" else "test_probe.py")).write_text(
        "import pytest\n"
        + ("def test_probe(): pass\n" if missing else
           "@pytest.mark.skip(reason='explicit acceptance probe')\ndef test_probe(): pass\n")
    )
    command = [sys.executable, "-I", "-m", "pytest", str(tmp_path), "-q",
               "--confcutdir", str(tmp_path)]
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
    (tmp_path / "conftest.py").write_text(isolated_hooks(
        tmp_path, provider_present=provider_present, demo_present=False))
    (tmp_path / "test_gate.py").write_text(Path(__file__).read_text())
    result = run_probe([sys.executable, "-I", "-m", "pytest", str(tmp_path), "-q",
                        "--confcutdir", str(tmp_path), "-k", "test_required_runtime_gate"],
                       tmp_path, monkeypatch)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "6 passed" in result.stdout and "skipped" not in result.stdout
