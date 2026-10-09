"""TC-017-06: allowed package reads, forbidden effects and real pytest gates."""

import builtins
import io
import os
import shutil
import sys
import time
from pathlib import Path

import pytest
from initial_capabilities_support import RESOURCE, initial_required
from inventory_support import ROOT

pytestmark = initial_required


def test_only_fixed_read_and_no_other_effects(initial_api, monkeypatch):
    # Warm stdlib resource discovery before instrumentation.
    initial_api.load_initial_capabilities()
    allowed = Path(initial_api.__file__).with_name(RESOURCE).resolve()
    attempted = []
    reads = []
    original_open, original_io, original_os = builtins.open, io.open, os.open

    def deny(*args, **kwargs):
        attempted.append(True)
        raise AssertionError("Initial catalogue attempted a forbidden effect")

    def checked(file, mode):
        if any(c in mode for c in "wax+") or Path(file).resolve() != allowed:
            deny()
        reads.append(allowed)

    def guarded_open(file, mode="r", *args, **kwargs):
        checked(file, mode)
        return original_open(file, mode, *args, **kwargs)

    def guarded_io(file, mode="r", *args, **kwargs):
        checked(file, mode)
        return original_io(file, mode, *args, **kwargs)

    def guarded_os(file, flags, *args, **kwargs):
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            return deny()
        checked(file, "r")
        return original_os(file, flags, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", guarded_open)
        patch.setattr(io, "open", guarded_io)
        patch.setattr(os, "open", guarded_os)
        patch.setattr(os, "getenv", deny)
        for name in ("time", "monotonic", "perf_counter", "sleep"):
            patch.setattr(time, name, deny)
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
        ):
            patch.setattr(os, name, deny, raising=False)
        patch.setattr(Path, "write_text", deny)
        patch.setattr(Path, "write_bytes", deny)
        cat = initial_api.load_initial_capabilities()
        assert cat.validate_payload(
            "home.switchable", 1, "action_input", "set_on", {"is_on": False}
        ) == {"is_on": False}
    assert reads == [allowed] and not attempted


def test_import_does_not_read_catalogue(initial_api, launch):
    script = """
import importlib.resources
import state_schema.capability
import sys
attempts = []
def deny(*args, **kwargs):
    attempts.append(True)
    raise AssertionError("import attempted resource discovery")
importlib.resources.files = deny
def audit(event, args):
    if event == "open" and str(args[0]).endswith("initial_capabilities.v1.json"):
        deny()
sys.addaudithook(audit)
import state_schema.initial_capabilities
assert not attempts
"""
    result = launch([sys.executable, "-B", "-c", script], cwd=ROOT)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("present", [False, True])
def test_actual_required_gate(tmp_path, launch, present):
    isolated = tmp_path / "isolated"
    isolated.mkdir()
    tests = ROOT / "libs/state-schema/tests"
    for name in ("conftest.py", "binding_support.py", "inventory_support.py"):
        shutil.copy2(tests / name, isolated / name)
    stub = isolated / "state_schema"
    stub.mkdir()
    (stub / "__init__.py").write_text("")
    (stub / "home_inventory.py").write_text("")
    (stub / "capability.py").write_text("")
    if present:
        (stub / "initial_capabilities.py").write_text("")
    (isolated / "test_placeholder.py").write_text(
        'import pytest\n@pytest.mark.skip(reason="required-case")\ndef test_case(): pass\n'
        if present
        else "def test_case(): pass\n"
    )
    result = launch(
        [
            sys.executable,
            "-m",
            "pytest",
            str(isolated),
            "--require-initial-capabilities-runtime",
            "-q",
        ],
        env=dict(os.environ, PYTHONPATH=str(isolated)),
        cwd=isolated,
    )
    assert result.returncode != 0
    assert (
        "1 skipped" in result.stdout
        if present
        else "initial Capability runtime is missing" in result.stderr
    )
