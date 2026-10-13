"""Counted ambient-effect denial and explicit missing-runtime acceptance gate."""

import importlib.util
import os
import random
import socket
import subprocess
import time
import urllib.request

import pytest


def available():
    try:
        return importlib.util.find_spec("home_device_fabric") is not None
    except ModuleNotFoundError:
        return False


def pytest_addoption(parser):
    parser.addoption("--require-provider-runtime", action="store_true", default=False)
    parser.addoption("--require-demo-runtime", action="store_true", default=False)
    parser.addoption("--require-conformance-runtime", action="store_true", default=False)
    parser.addoption("--require-ha-configuration-runtime", action="store_true", default=False)


def demo_available():
    try:
        return all(
            importlib.util.find_spec("home_device_fabric." + name) is not None
            for name in ("scenarios", "caller", "demo")
        )
    except ModuleNotFoundError:
        return False


def conformance_available():
    try:
        return all(
            importlib.util.find_spec(name) is not None
            for name in (
                "home_device_fabric.conformance",
                "home_device_fabric.conformance_fixtures",
                "home_device_fabric.conformance_catalogue",
                "state_schema.action_contracts",
                "state_schema.canonical_state",
                "state_schema.provider_contracts",
            )
        )
    except ModuleNotFoundError:
        return False


def ha_configuration_available():
    try:
        return all(importlib.util.find_spec(name) is not None for name in (
            "home_device_fabric.ha_configuration", "state_schema.provider_contracts",
            "state_schema.action_contracts", "state_schema.canonical_state",
        ))
    except ModuleNotFoundError:
        return False


def pytest_collection_modifyitems(config, items):
    if config.getoption("--require-ha-configuration-runtime") and not ha_configuration_available():
        raise pytest.UsageError("REQ-022 ha-configuration runtime required but absent")
    if not ha_configuration_available():
        for item in items:
            if item.path.name == "test_ha_configuration.py":
                item.add_marker(pytest.mark.skip(reason="REQ-022 ha-configuration runtime absent"))
    if config.getoption("--require-conformance-runtime") and not conformance_available():
        raise pytest.UsageError("REQ-021 conformance runtime required but absent")
    if not conformance_available():
        for item in items:
            if item.path.name == "test_conformance.py":
                item.add_marker(pytest.mark.skip(reason="REQ-021 conformance runtime absent"))
    if config.getoption("--require-demo-runtime") and not demo_available():
        raise pytest.UsageError("REQ-020 demo runtime required but absent")
    if not demo_available():
        for item in items:
            if item.path.name == "test_demo.py":
                item.add_marker(pytest.mark.skip(reason="REQ-020 demo runtime absent"))
    if not available():
        if config.getoption("--require-provider-runtime"):
            raise pytest.UsageError("REQ-019 provider runtime required but absent")
        for item in items:
            # Gate probes use local stubs and must execute even without the runtime.
            if item.path.name != "test_gate.py":
                item.add_marker(
                    pytest.mark.skip(reason="REQ-019 runtime absent; acceptance pending")
                )


def pytest_sessionfinish(session, exitstatus):
    if (
        session.config.getoption("--require-provider-runtime")
        or session.config.getoption("--require-demo-runtime")
        or session.config.getoption("--require-conformance-runtime")
        or session.config.getoption("--require-ha-configuration-runtime")
    ):
        reporter = session.config.pluginmanager.getplugin("terminalreporter")
        if reporter and reporter.stats.get("skipped"):
            session.exitstatus = pytest.ExitCode.TESTS_FAILED
    if session.config.getoption("--require-conformance-runtime") and exitstatus not in (
        pytest.ExitCode.USAGE_ERROR,
        pytest.ExitCode.INTERRUPTED,
    ):
        # Mandatory runtime inventory is verified even if pytest selection omits its TCs.
        try:
            from home_device_fabric.conformance import run_conformance, validate_report

            complete = validate_report(run_conformance())
        except Exception:
            complete = False
        if not complete:
            session.exitstatus = pytest.ExitCode.TESTS_FAILED


@pytest.fixture(autouse=True)
def offline(monkeypatch, request):
    # This guard covers network/process/clock/random effects, not all file I/O.
    # test_demo.test_runtime_file_environment_datetime_denial separately denies
    # file/env/datetime access after explicit fixed catalogue resource loading.
    # Import modules before denying Python's import machinery reads.
    if available():
        import home_device_fabric  # noqa: F401
    attempts = []

    def deny(*args, **kwargs):
        attempts.append(1)
        raise AssertionError("ambient effect denied")

    with monkeypatch.context() as patch:
        for module, names in [
            (socket, ("create_connection", "getaddrinfo")),
            (subprocess, ("Popen",)),
            (urllib.request, ("urlopen",)),
            (time, ("time", "time_ns", "monotonic", "monotonic_ns", "perf_counter",
                    "perf_counter_ns", "process_time", "process_time_ns", "sleep")),
            (random, ("random", "randint", "randrange", "getrandbits")),
            (os, ("getenv", "system", "urandom")),
        ]:
            for name in names:
                if module is subprocess and request.node.get_closest_marker("cli_boundary"):
                    continue  # Only explicit CLI subprocess tests cross this boundary.
                patch.setattr(module, name, deny)
        patch.setattr(socket.socket, "connect", deny)
        patch.setattr(socket.socket, "connect_ex", deny)
        yield attempts
    assert not attempts, "forbidden effects attempted even if swallowed"
