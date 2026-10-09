"""TC-018-06: immutable boundaries, privacy, purity and real required-mode gates."""

import builtins
import dataclasses
import io
import os
import shutil
import sys
import time
from pathlib import Path

import pytest
from action_support import evidence, make, reject, request, required, result, running
from inventory_support import ROOT

pytestmark = required


def test_frozen_records_and_snapshots(action_api, inventory, initial_cat):
    r = request()
    record = action_api.ActionRequest.from_dict(r)
    t = make(action_api, inventory, initial_cat, r)
    model = action_api.Task.from_dict(t)
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.trace_id = 'changed'
    with pytest.raises(dataclasses.FrozenInstanceError):
        model.state = 'succeeded'
    r['arguments']['is_on'] = True
    assert record.to_dict()['arguments']['is_on'] is False
    for snapshot in [record.to_dict(), record.to_dict()]:
        snapshot['arguments']['is_on'] = True
    assert record.to_dict()['arguments']['is_on'] is False
    snapshot = model.to_dict()
    snapshot['request']['arguments']['is_on'] = True
    snapshot['requester']['role'] = 'admin'
    assert model.to_dict() == t
    rt = running(action_api, inventory, initial_cat)
    out = result(rt, 'succeeded', evidence=evidence(rt, 'state'))
    parsed = action_api.ActionResult.from_dict(out)
    out['evidence']['state']['reported_state'].clear()
    assert parsed.to_dict()['evidence']['state']['reported_state']


@pytest.mark.parametrize('value', [float('nan'), float('inf'), float('-inf'), object(), (1,)])
def test_bad_json(action_api, value):
    r = request()
    r['arguments'] = {'private-input': value}
    reject(action_api, lambda: action_api.ActionRequest.from_dict(r), private=('private-input',))


def test_cycles_depth_and_unknown_keys(action_api):
    r = request()
    r['arguments']['cycle'] = r['arguments']
    reject(action_api, lambda: action_api.ActionRequest.from_dict(r))
    nested = []
    for _ in range(17):
        nested = [nested]
    r['arguments'] = {'private-input': nested}
    reject(action_api, lambda: action_api.ActionRequest.from_dict(r), private=('private-input',))
    r = {**request(), 'SECRET-KEY': 'SECRET-VALUE'}
    reject(action_api, lambda: action_api.ActionRequest.from_dict(r),
           private=('SECRET-KEY', 'SECRET-VALUE'))


def test_pure_helpers_without_files_clocks_environment(action_api, inventory, initial_cat, monkeypatch):
    attempts = []

    def deny(*args, **kwargs):
        attempts.append(True)
        raise AssertionError('Action contract attempted forbidden effect')

    with monkeypatch.context() as patch:
        for mod, names in [(builtins, ('open',)), (io, ('open',)),
                           (os, ('open', 'getenv', 'remove', 'rename', 'mkdir', 'rmdir',
                                 'truncate', 'chmod', 'chown', 'utime')),
                           (time, ('time', 'monotonic', 'perf_counter', 'sleep'))]:
            for name in names:
                patch.setattr(mod, name, deny, raising=False)
        t = running(action_api, inventory, initial_cat)
        out = result(t, 'succeeded', evidence=evidence(t, 'state'))
        done = action_api.transition_task(t, out, inventory=inventory, catalogue=initial_cat)
        assert action_api.validate_task(done, inventory=inventory, catalogue=initial_cat) == done
        assert action_api.compare_idempotency(done, request(), requester=done['requester'],
                                              inventory=inventory, catalogue=initial_cat) == 'replay'
        reject(action_api, lambda: action_api.transition_task(
            t, result(t, 'succeeded', evidence=evidence(t)),
            inventory=inventory, catalogue=initial_cat))
    assert not attempts


def test_import_no_application_io(action_api, launch):
    script = '''
import sys
import state_schema.capability
import state_schema.canonical_state
attempts = []
def audit(event, args):
    forbidden = event.startswith('socket.') or event in ('subprocess.Popen', 'os.system')
    if event == 'open':
        forbidden = not str(args[0]).endswith(('.py', '.pyc'))
    if forbidden:
        attempts.append(event)
        raise AssertionError('import effect')
sys.addaudithook(audit)
import state_schema.action_contracts
assert not attempts
'''
    out = launch([sys.executable, '-B', '-c', script], cwd=ROOT,
                 env=dict(os.environ, PYTHONPATH=str(ROOT / 'libs/state-schema/src')))
    assert out.returncode == 0, out.stderr


@pytest.mark.parametrize('present', [False, True])
def test_actual_required_gate(tmp_path, launch, present):
    isolated = tmp_path / 'isolated'
    isolated.mkdir()
    for name in ['conftest.py', 'inventory_support.py', 'binding_support.py']:
        shutil.copy2(ROOT / 'libs/state-schema/tests' / name, isolated / name)
    stub = isolated / 'state_schema'
    stub.mkdir()
    (stub / '__init__.py').write_text('')
    (stub / 'home_inventory.py').write_text('')
    if present:
        (stub / 'action_contracts.py').write_text('')
    (isolated / 'test_placeholder.py').write_text(
        'import pytest\n@pytest.mark.skip(reason="required-case")\ndef test_case(): pass\n'
        if present else 'def test_case(): pass\n')
    out = launch([sys.executable, '-m', 'pytest', str(isolated), '--require-action-runtime', '-q'],
                 cwd=isolated, env=dict(os.environ, PYTHONPATH=str(isolated)))
    assert out.returncode != 0
    assert ('1 skipped' in out.stdout if present else 'Action runtime is missing' in out.stderr)
