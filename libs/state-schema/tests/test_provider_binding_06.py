"""TC-014-06: offline purity, public boundary and acceptance-mode guards."""

import ast
import builtins
import io
import os
from pathlib import Path

import pytest
from binding_support import binding, binding_required, collection
from inventory_support import ROOT

pytestmark = binding_required


def test_pure_validation(binding_api, inventory, monkeypatch):
    calls = []

    def deny(*args, **kwargs):
        calls.append(True)
        raise AssertionError("binding validation attempted filesystem mutation")

    real_open = builtins.open
    real_io_open = io.open
    real_os_open = os.open

    def guarded_open(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in "wax+"):
            return deny()
        return real_open(file, mode, *args, **kwargs)

    def guarded_io_open(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in "wax+"):
            return deny()
        return real_io_open(file, mode, *args, **kwargs)

    def guarded_os_open(file, flags, *args, **kwargs):
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            return deny()
        return real_os_open(file, flags, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", guarded_open)
        patch.setattr(io, "open", guarded_io_open)
        patch.setattr(os, "open", guarded_os_open)
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
        assert binding_api.validate_bindings(collection(binding()), inventory=inventory)
        with pytest.raises(binding_api.BindingError):
            binding_api.validate_bindings(
                collection(binding(device="unknown-device")), inventory=inventory
            )
    assert not calls


def test_module_has_only_contract_imports_and_no_dispatch(binding_api):
    tree = ast.parse(Path(binding_api.__file__).read_text())
    allowed = {"__future__", "dataclasses", "re", "typing", "home_inventory"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(alias.name.split(".")[0] in allowed for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] in allowed
    for name in ("dispatch", "execute", "replace_binding", "connect", "load_bindings"):
        assert not hasattr(binding_api, name)


def test_acceptance_option_fails_when_runtime_is_absent(tmp_path, launch):
    # Isolate the actual conftest and guard-support modules, omitting binding runtime.
    import shutil
    import sys

    isolated = tmp_path / "isolated"
    isolated.mkdir()
    tests = ROOT / "libs/state-schema/tests"
    for name in ("conftest.py", "binding_support.py", "inventory_support.py"):
        shutil.copy2(tests / name, isolated / name)
    (isolated / "test_placeholder.py").write_text("def test_placeholder():\n    assert True\n")
    stub = isolated / "state_schema"
    stub.mkdir()
    (stub / "__init__.py").write_text("")
    (stub / "home_inventory.py").write_text("")
    env = dict(os.environ, PYTHONPATH=str(isolated))
    result = launch(
        [sys.executable, "-m", "pytest", str(isolated), "--require-binding-runtime", "-q"],
        env=env,
        cwd=isolated,
    )
    assert result.returncode != 0
    assert "binding runtime is missing" in result.stderr


def test_acceptance_option_rejects_skipped_tests(tmp_path, launch):
    import shutil
    import sys

    isolated = tmp_path / "isolated"
    isolated.mkdir()
    for name in ("conftest.py", "binding_support.py", "inventory_support.py"):
        shutil.copy2(ROOT / "libs/state-schema/tests" / name, isolated / name)
    (isolated / "test_skip.py").write_text(
        'import pytest\n@pytest.mark.skip(reason="fixture")\ndef test_skip():\n    pass\n'
    )
    env = dict(os.environ, PYTHONPATH=str(ROOT / "libs/state-schema/src"))
    result = launch(
        [sys.executable, "-m", "pytest", str(isolated), "--require-binding-runtime", "-q"],
        env=env,
        cwd=isolated,
    )
    assert result.returncode != 0
    assert "1 skipped" in result.stdout
