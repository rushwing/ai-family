"""TC-016-06: actual offline boundaries and absent/skip acceptance probes."""

import ast
import builtins
import io
import json
import os
import shutil
import sys
from pathlib import Path

import pytest
from capability_support import capability_required, catalogue, descriptor
from inventory_support import ROOT

pytestmark = capability_required


@pytest.mark.parametrize("link_present", [True, False])
def test_pure_factories_and_failures(capability_api, monkeypatch, link_present):
    if not link_present:
        monkeypatch.delattr(os, "link", raising=False)
    attempts = []

    def deny(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("Capability attempted filesystem mutation")

    original_open, original_io, original_os = builtins.open, io.open, os.open

    def guarded_open(file, mode="r", *args, **kwargs):
        return (
            deny() if any(c in mode for c in "wax+") else original_open(file, mode, *args, **kwargs)
        )

    def guarded_io(file, mode="r", *args, **kwargs):
        return (
            deny() if any(c in mode for c in "wax+") else original_io(file, mode, *args, **kwargs)
        )

    def guarded_os(file, flags, *args, **kwargs):
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            return deny()
        return original_os(file, flags, *args, **kwargs)

    api = capability_api
    data = descriptor()
    text = json.dumps(catalogue(data))
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
        ):
            patch.setattr(os, name, deny, raising=False)
        patch.setattr(Path, "write_text", deny)
        patch.setattr(Path, "write_bytes", deny)
        assert api.validate_capability(data) == data
        parsed = api.load_capabilities_json(text)
        assert parsed.validate_payload(
            "demo.power", 1, "action_input", "set_power", {"power": False}
        ) == {"power": False}
        assert api.validate_schema({"type": "boolean"}) == {"type": "boolean"}
        assert api.validate_payload({"type": "boolean"}, False) is False
        for call in (
            lambda: api.load_capability_json("{"),
            lambda: api.validate_capability({"PRIVATE_DATA": True}),
            lambda: parsed.validate_payload(
                "demo.power", 1, "action_input", "set_power", {"power": 0}
            ),
        ):
            with pytest.raises(api.CapabilityError):
                call()
    assert not attempts


def test_module_boundary(capability_api, state_api):
    # Keep offline modules independent while guarding their common member grammar.
    assert capability_api._MEMBER.pattern == state_api._PROPERTY.pattern
    assert capability_api._MEMBER.flags == state_api._PROPERTY.flags
    tree = ast.parse(Path(capability_api.__file__).read_text())
    allowed = {"__future__", "dataclasses", "json", "math", "re", "typing"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(alias.name.split(".")[0] in allowed for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] in allowed
    for name in ("dispatch", "execute", "connect", "save", "evaluate_completion"):
        assert not hasattr(capability_api, name)


@pytest.mark.parametrize("present", [False, True])
def test_actual_acceptance_gate(tmp_path, launch, present):
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
        (stub / "capability.py").write_text("")
    (isolated / "test_placeholder.py").write_text(
        'import pytest\n@pytest.mark.skip(reason="required-case")\ndef test_case(): pass\n'
        if present
        else "def test_case(): pass\n"
    )
    result = launch(
        [sys.executable, "-m", "pytest", str(isolated), "--require-capability-runtime", "-q"],
        env=dict(os.environ, PYTHONPATH=str(isolated)),
        cwd=isolated,
    )
    assert result.returncode != 0
    assert (
        ("1 skipped" in result.stdout)
        if present
        else ("Capability runtime is missing" in result.stderr)
    )
