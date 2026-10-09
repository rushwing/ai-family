"""TC-015-06: pure contracts and missing-runtime/skip acceptance gates."""

import ast
import builtins
import io
import os
import shutil
import sys
from pathlib import Path

import pytest
from inventory_support import ROOT
from state_support import collection, observation, state, state_required

pytestmark = state_required


def test_pure_contract_helpers(state_api, inventory, monkeypatch):
    calls = []

    def deny(*args, **kwargs):
        calls.append(True)
        raise AssertionError("State contract attempted filesystem mutation")

    real_open, real_io_open, real_os_open = builtins.open, io.open, os.open

    def guarded_open(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in "wax+"):
            return deny()
        return real_open(file, mode, *args, **kwargs)

    def guarded_io(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in "wax+"):
            return deny()
        return real_io_open(file, mode, *args, **kwargs)

    def guarded_os(file, flags, *args, **kwargs):
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            return deny()
        return real_os_open(file, flags, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", guarded_open)
        patch.setattr(io, "open", guarded_io)
        patch.setattr(os, "open", guarded_os)
        for name in (
            "remove",
            "rename",
            "mkdir",
            "rmdir",
            "link",
            "symlink",
            "truncate",
            "chmod",
            "chown",
            "utime",
            "system",
        ):
            patch.setattr(os, name, deny)
        patch.setattr(Path, "write_text", deny)
        patch.setattr(Path, "write_bytes", deny)
        assert state_api.validate_states(collection(state()), inventory=inventory)
        assert state_api.evaluate_convergence(state(), current_epoch=1) == "confirmed"
        assert state_api.apply_state_update(
            state(), current_epoch=1, reported_state={"power": observation(True, 3)}
        )
        with pytest.raises(state_api.StateError):
            state_api.validate_state({"PRIVATE_DATA": True})
        with pytest.raises(state_api.StateError):
            state_api.apply_state_update(
                state(), current_epoch=1, reported_state={"power": observation(True, 2)}
            )
    assert not calls


def test_module_boundary(state_api):
    tree = ast.parse(Path(state_api.__file__).read_text())
    allowed = {"__future__", "dataclasses", "datetime", "math", "re", "typing", "home_inventory"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(alias.name.split(".")[0] in allowed for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] in allowed
    for name in ("dispatch", "execute", "connect", "ack", "save", "load_state"):
        assert not hasattr(state_api, name)


@pytest.mark.parametrize("present", [False, True])
def test_acceptance_requires_present_runtime_and_no_skips(tmp_path, launch, present):
    isolated = tmp_path / "isolated"
    isolated.mkdir()
    tests = ROOT / "libs/state-schema/tests"
    for name in ("conftest.py", "binding_support.py", "inventory_support.py"):
        shutil.copy2(tests / name, isolated / name)
    stub = isolated / "state_schema"
    stub.mkdir()
    (stub / "__init__.py").write_text("")
    (stub / "home_inventory.py").write_text("")
    if present:
        (stub / "canonical_state.py").write_text("")
    (isolated / "test_placeholder.py").write_text(
        'import pytest\n@pytest.mark.skip(reason="required-case")\ndef test_case(): pass\n'
        if present
        else "def test_case(): pass\n"
    )
    result = launch(
        [sys.executable, "-m", "pytest", str(isolated), "--require-state-runtime", "-q"],
        env=dict(os.environ, PYTHONPATH=str(isolated)),
        cwd=isolated,
    )
    assert result.returncode != 0
    assert (
        ("1 skipped" in result.stdout) if present else ("State runtime is missing" in result.stderr)
    )
