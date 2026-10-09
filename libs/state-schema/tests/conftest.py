"""Isolated fixture copies and fail-fast instrumentation for offline contracts."""

import importlib
import json
import os
import socket
import subprocess
import urllib.request
from importlib.util import find_spec

import pytest
from binding_support import BINDING_AVAILABLE
from inventory_support import EXAMPLE, RUNTIME_AVAILABLE


@pytest.fixture
def api():
    # Only module absence is gated by the module-level skipif markers. Broken
    # imports, missing exports and installed-but-incomplete implementations fail.
    module = importlib.import_module('state_schema.home_inventory')
    for export in ('validate_inventory', 'load_inventory', 'resolve_targets', 'InventoryError'):
        assert hasattr(module, export), f'Missing reviewed test seam: {export}'
    return module


@pytest.fixture
def binding_api():
    module = importlib.import_module('state_schema.provider_binding')
    for export in ('ProviderBinding', 'BindingCollection', 'BindingError',
                   'validate_binding', 'validate_bindings'):
        assert hasattr(module, export), f'Missing binding test seam: {export}'
    return module


@pytest.fixture
def state_api():
    module = importlib.import_module('state_schema.canonical_state')
    for export in ('DeviceState', 'StateCollection', 'StateError', 'Ordering',
                   'Observation', 'Availability', 'DesiredState', 'validate_state',
                   'validate_states', 'apply_state_update', 'evaluate_convergence'):
        assert hasattr(module, export), f'Missing State test seam: {export}'
    return module


@pytest.fixture
def capability_api():
    module = importlib.import_module('state_schema.capability')
    for export in ('Schema', 'Property', 'Action', 'Event', 'CompletionPolicy',
                   'TargetSource', 'CapabilityDescriptor', 'CapabilityCatalogue',
                   'CapabilityError', 'validate_capability', 'validate_capabilities',
                   'load_capability_json', 'load_capabilities_json',
                   'validate_schema', 'validate_payload'):
        assert hasattr(module, export), f'Missing Capability seam: {export}'
    return module


@pytest.fixture
def initial_api():
    module = importlib.import_module('state_schema.initial_capabilities')
    assert callable(getattr(module, 'load_initial_capabilities', None)), (
        'Missing initial catalogue seam'
    )
    return module


@pytest.fixture
def inventory():
    return json.loads(EXAMPLE.read_text(encoding='utf-8'))


@pytest.fixture(autouse=True)
def offline_guard(monkeypatch, request):
    attempts = 0
    expected_marker = request.node.get_closest_marker("expected_offline_attempts")
    expected = expected_marker.args[0] if expected_marker else 0

    def deny(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        raise AssertionError('Inventory code attempted network or action-process execution')

    with monkeypatch.context() as patch:
        patch.setattr(socket.socket, 'connect', deny)
        patch.setattr(socket.socket, 'connect_ex', deny)
        patch.setattr(socket, 'create_connection', deny)
        patch.setattr(socket, 'getaddrinfo', deny)
        patch.setattr(urllib.request, 'urlopen', deny)
        patch.setattr(subprocess, 'Popen', deny)
        for name in dir(os):
            if (name in ('system', 'fork', 'forkpty')
                    or name.startswith(('exec', 'spawn', 'posix_spawn'))):
                if callable(getattr(os, name)):
                    patch.setattr(os, name, deny)
        # Expose only an integer reader; callers cannot clear the evidence.
        # Infrastructure probes predeclare the exact expected count by marker.
        yield lambda: attempts
    assert attempts == expected, (
        'Forbidden effects were attempted, even if their errors were caught'
    )


# Save before the autouse offline guard patches parent-side process creation.
_REAL_POPEN = subprocess.Popen


@pytest.fixture
def launch(monkeypatch):
    def run(command, **kwargs):
        with monkeypatch.context() as patch:
            patch.setattr(subprocess, 'Popen', _REAL_POPEN)
            return subprocess.run(command, capture_output=True, text=True, timeout=20, **kwargs)
    return run


@pytest.fixture
def cli(tmp_path, launch):
    import os
    import sys

    from inventory_support import CLI, ROOT

    guard = tmp_path / 'child-guard'
    guard.mkdir()
    effects = guard / 'effects.log'
    # The log is opened before installing the hook so even swallowed guard
    # exceptions leave evidence visible to the parent test.
    (guard / 'sitecustomize.py').write_text('''
import os
import sys
log = open(os.environ['INVENTORY_EFFECT_LOG'], 'a', encoding='utf-8')
def audit(event, args):
    forbidden = event.startswith('socket.') or event in (
        'subprocess.Popen', 'os.system', 'os.posix_spawn', 'os.exec', 'os.fork', 'os.forkpty',
        'os.remove', 'os.rename', 'os.mkdir', 'os.rmdir', 'os.link',
        'os.symlink', 'os.truncate', 'os.chmod', 'os.chown', 'os.utime',
    )
    if event == 'open':
        mode, flags = args[1], args[2]
        forbidden = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
        forbidden = forbidden or (isinstance(mode, str) and any(c in mode for c in 'wax+'))
    if forbidden:
        log.write(event + '\\n')
        log.flush()
        raise RuntimeError('offline inventory guard denied ' + event)
sys.addaudithook(audit)
''', encoding='utf-8')
    environment = dict(os.environ)
    environment.update(
        PYTHONDONTWRITEBYTECODE='1',
        PYTHONPATH=os.pathsep.join([str(guard), str(ROOT / 'libs/state-schema/src')]),
        INVENTORY_EFFECT_LOG=str(effects),
    )

    def run(path):
        result = launch([sys.executable, '-B', *CLI, str(path)], env=environment, cwd=ROOT)
        assert effects.exists(), 'Child offline guard was not loaded'
        assert not effects.read_text(), 'CLI attempted forbidden effects'
        return result
    return run



def pytest_addoption(parser):
    parser.addoption('--require-action-runtime', action='store_true',
                     help='REQ-018 acceptance: fail on absent Action runtime or skipped tests')
    parser.addoption('--require-initial-capabilities-runtime', action='store_true',
                     help='REQ-017 acceptance: fail on absent initial catalogue or skipped tests')
    parser.addoption('--require-capability-runtime', action='store_true',
                     help='REQ-016 acceptance: fail on absent Capability runtime or skipped tests')
    parser.addoption('--require-state-runtime', action='store_true',
                     help='REQ-015 acceptance: fail on absent State runtime or skipped tests')
    parser.addoption('--require-binding-runtime', action='store_true',
                     help='REQ-014 acceptance: fail on absent binding runtime or skipped tests')
    parser.addoption('--require-inventory-runtime', action='store_true',
                     help='Acceptance mode: fail on absent inventory runtime or skipped tests')


def pytest_sessionstart(session):
    if (session.config.getoption('--require-action-runtime')
            and find_spec('state_schema.action_contracts') is None):
        raise pytest.UsageError('REQ-018 Action runtime is missing; acceptance cannot pass')
    if (session.config.getoption('--require-initial-capabilities-runtime')
            and find_spec('state_schema.initial_capabilities') is None):
        raise pytest.UsageError(
            'REQ-017 initial Capability runtime is missing; acceptance cannot pass'
        )
    if (session.config.getoption('--require-capability-runtime')
            and find_spec('state_schema.capability') is None):
        raise pytest.UsageError('REQ-016 Capability runtime is missing; acceptance cannot pass')
    if (session.config.getoption('--require-state-runtime')
            and find_spec('state_schema.canonical_state') is None):
        raise pytest.UsageError('REQ-015 State runtime is missing; acceptance cannot pass')
    if session.config.getoption('--require-binding-runtime') and not BINDING_AVAILABLE:
        raise pytest.UsageError('REQ-014 binding runtime is missing; acceptance cannot pass')
    if session.config.getoption('--require-inventory-runtime') and not RUNTIME_AVAILABLE:
        raise pytest.UsageError('REQ-013 inventory runtime is missing; acceptance cannot pass')


def pytest_sessionfinish(session, exitstatus):
    if (session.config.getoption('--require-inventory-runtime')
            or session.config.getoption('--require-binding-runtime')
            or session.config.getoption('--require-state-runtime')
            or session.config.getoption('--require-capability-runtime')
            or session.config.getoption('--require-initial-capabilities-runtime')
            or session.config.getoption('--require-action-runtime')):
        reporter = session.config.pluginmanager.getplugin('terminalreporter')
        if reporter and reporter.stats.get('skipped'):
            session.exitstatus = pytest.ExitCode.TESTS_FAILED


@pytest.fixture
def action_api():
    module = importlib.import_module('state_schema.action_contracts')
    for export in ('ActionError', 'ActionRequest', 'RequesterContext', 'ActionResult', 'Task',
                   'validate_request', 'validate_task', 'validate_result', 'create_task',
                   'transition_task', 'compare_idempotency'):
        assert hasattr(module, export), f'Missing Action seam: {export}'
    return module


@pytest.fixture
def initial_cat():
    return importlib.import_module('state_schema.initial_capabilities').load_initial_capabilities().to_dict()
