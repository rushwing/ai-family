"""Exercise the test infrastructure even while all runtime TCs are skipped."""

import os
import socket
import subprocess
import sys

import pytest
from inventory_support import ROOT


@pytest.mark.parametrize('action', [
    "import socket; socket.create_connection(('127.0.0.1', 9))",
    "open('forbidden-write', 'w')",
    "import subprocess; subprocess.run(['true'])",
    "import os; os.remove('nonexistent')",
])
def test_child_audit_guard_records_swallowed_effects(tmp_path, launch, cli, action):
    # Use the exact child guard installed by the CLI fixture, but do not pretend
    # this infrastructure check is a runtime acceptance test.
    guard = tmp_path / 'child-guard'
    env = dict(os.environ, PYTHONPATH=str(guard), PYTHONDONTWRITEBYTECODE='1',
               INVENTORY_EFFECT_LOG=str(guard / 'effects.log'))
    script = f'try:\n {action}\nexcept Exception:\n pass\n'
    result = launch([sys.executable, '-B', '-c', script], env=env, cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert (guard / 'effects.log').read_text().strip()
    assert not (tmp_path / 'forbidden-write').exists()


def test_parent_guard_is_installed(offline_guard):
    with pytest.raises(AssertionError, match='network or action-process'):
        socket.create_connection(('127.0.0.1', 9))
    # This test intentionally exercised the deny hook; the guard's teardown
    # still rejects swallowed attempts in all other tests.
    assert len(offline_guard) == 1
    offline_guard.clear()


def test_test_launcher_can_run_read_only_commands(launch):
    result = launch(['git', 'check-ignore', '--no-index',
                     'test.home-inventory.local.json'], cwd=ROOT)
    assert result.returncode == 0
    assert 'test.home-inventory.local.json' in result.stdout


def test_parent_guard_blocks_processes(offline_guard):
    with pytest.raises(AssertionError, match='network or action-process'):
        subprocess.run(['true'])
    assert len(offline_guard) == 1
    offline_guard.clear()
