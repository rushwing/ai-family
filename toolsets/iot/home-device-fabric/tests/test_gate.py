"""Exercise the actual pytest hooks in isolated acceptance-gate subprocesses."""

import subprocess
import sys
import time
from pathlib import Path

import pytest

_POPEN = subprocess.Popen
_SLEEP = time.sleep


@pytest.mark.parametrize("missing,required,exitcode", [(True, False, 0), (True, True, 4),
                                                      (False, True, 1)])
@pytest.mark.tc019_06
def test_required_runtime_gate(tmp_path, monkeypatch, missing, required, exitcode):
    hooks = Path(__file__).with_name("conftest.py").read_text()
    if missing:
        hooks += "\ndef available():\n    return False\n"
    (tmp_path / "conftest.py").write_text(hooks)
    (tmp_path / "test_probe.py").write_text(
        "import pytest\n"
        + ("def test_probe(): pass\n" if missing else
           "@pytest.mark.skip(reason='explicit acceptance probe')\ndef test_probe(): pass\n")
    )
    command = [sys.executable, "-m", "pytest", str(tmp_path), "-q", "--confcutdir", str(tmp_path)]
    if required:
        command.append("--require-provider-runtime")
    # This subprocess tests the gate, not provider behavior. Runtime calls remain
    # under the counted offline guard in the provider tests and child hooks.
    with monkeypatch.context() as patch:
        patch.setattr(subprocess, "Popen", _POPEN)
        patch.setattr(time, "sleep", _SLEEP)
        result = subprocess.run(command, capture_output=True, text=True, timeout=20, cwd=tmp_path)
    assert result.returncode == exitcode, result.stdout + result.stderr
    if missing and required:
        assert "provider runtime required but absent" in result.stderr
    else:
        assert "1 skipped" in result.stdout
