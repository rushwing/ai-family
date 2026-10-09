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


@pytest.mark.expected_offline_attempts(1)
def test_parent_guard_is_installed(offline_guard):
    with pytest.raises(AssertionError, match='network or action-process'):
        socket.create_connection(('127.0.0.1', 9))
    # This infrastructure probe predeclares one intentional denied attempt.
    assert offline_guard() == 1


def test_test_launcher_can_run_read_only_commands(launch):
    result = launch(['git', 'check-ignore', '--no-index',
                     'test.home-inventory.local.json'], cwd=ROOT)
    assert result.returncode == 0
    assert 'test.home-inventory.local.json' in result.stdout


@pytest.mark.expected_offline_attempts(1)
def test_parent_guard_blocks_processes(offline_guard):
    with pytest.raises(AssertionError, match='network or action-process'):
        subprocess.run(['true'])
    assert offline_guard() == 1


@pytest.mark.expected_offline_attempts(1)
@pytest.mark.parametrize('channel', ['system', 'fork', 'posix_spawn'])
def test_parent_guard_blocks_os_process_channels(offline_guard, channel):
    # The guard supplies a deny hook only for supported OS APIs. This probe must
    # not skip on platforms lacking one: the unavailable path cannot launch.
    if not hasattr(os, channel):
        with pytest.raises(AssertionError, match='network or action-process'):
            socket.create_connection(('127.0.0.1', 9))
    else:
        with pytest.raises(AssertionError, match='network or action-process'):
            getattr(os, channel)()
    assert offline_guard() == 1
    assert not hasattr(offline_guard, 'clear')


def test_swallowed_attempts_fail_guard_teardown(tmp_path, launch):
    import shutil

    isolated = tmp_path / 'isolated-guard'
    isolated.mkdir()
    tests = ROOT / 'libs/state-schema/tests'
    for name in ('conftest.py', 'binding_support.py', 'inventory_support.py'):
        shutil.copy2(tests / name, isolated / name)
    package = isolated / 'state_schema'
    package.mkdir()
    (package / '__init__.py').write_text('')
    (package / 'home_inventory.py').write_text('')
    (isolated / 'test_swallowed.py').write_text('''
import os
import socket
import subprocess
import pytest
@pytest.mark.parametrize('channel', ['system', 'network', 'process'])
def test_swallowed(offline_guard, channel):
    try:
        if channel == 'system': os.system('true')
        elif channel == 'network': socket.create_connection(('127.0.0.1', 9))
        else: subprocess.run(['true'])
    except AssertionError:
        pass
    assert not hasattr(offline_guard, 'clear')
''')
    result = launch([sys.executable, '-m', 'pytest', '-q', str(isolated)],
                    env=dict(os.environ, PYTHONPATH=str(isolated)), cwd=isolated)
    assert result.returncode != 0
    assert 'Forbidden effects were attempted' in result.stdout
    assert '3 errors' in result.stdout
