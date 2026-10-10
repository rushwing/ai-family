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


def pytest_collection_modifyitems(config, items):
    if not available():
        if config.getoption("--require-provider-runtime"):
            raise pytest.UsageError("REQ-019 provider runtime required but absent")
        for item in items:
            item.add_marker(pytest.mark.skip(reason="REQ-019 runtime absent; acceptance pending"))


def pytest_sessionfinish(session, exitstatus):
    if session.config.getoption("--require-provider-runtime"):
        reporter = session.config.pluginmanager.getplugin("terminalreporter")
        if reporter and reporter.stats.get("skipped"):
            session.exitstatus = pytest.ExitCode.TESTS_FAILED


@pytest.fixture(autouse=True)
def offline(monkeypatch):
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
            (time, ("time", "monotonic", "perf_counter", "sleep")),
            (random, ("random", "randint", "randrange", "getrandbits")),
            (os, ("getenv", "system", "urandom")),
        ]:
            for name in names:
                patch.setattr(module, name, deny)
        patch.setattr(socket.socket, "connect", deny)
        patch.setattr(socket.socket, "connect_ex", deny)
        yield attempts
    assert not attempts, "forbidden effects attempted even if swallowed"
