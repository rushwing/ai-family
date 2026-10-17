"""Counted ambient-effect denial and explicit missing-runtime acceptance gate."""

import importlib
import importlib.util
import ipaddress
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
    parser.addoption("--require-ha-rest-runtime", action="store_true", default=False)
    parser.addoption("--require-ha-websocket-runtime", action="store_true", default=False)
    parser.addoption("--require-ha-health-runtime", action="store_true", default=False)
    parser.addoption("--require-ha-subscription-runtime", action="store_true", default=False)
    parser.addoption("--require-ha-normalization-runtime", action="store_true", default=False)


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


def ha_rest_available():
    try:
        for name in ("home_device_fabric.ha_rest", "httpx"):
            importlib.import_module(name)
        return True
    except (ImportError, ValueError):
        return False


def pytest_collection_modifyitems(config, items):
    for item in items:
        groups = sorted({mark.name for mark in item.iter_markers()
                         if mark.name.startswith("tc") and "_" in mark.name})
        if groups:
            item.user_properties.append(("tc_groups", ",".join(groups)))
    try:
        importlib.import_module("home_device_fabric.ha_websocket")
        websocket_error = None
    except ImportError:
        websocket_error = "absent"
    except Exception:
        websocket_error = "broken"
    if config.getoption("--require-ha-websocket-runtime") and websocket_error:
        raise pytest.UsageError("REQ-024 ha-websocket runtime required but " + websocket_error)
    if websocket_error:
        for item in items:
            if item.path.name == "test_ha_websocket.py":
                item.add_marker(pytest.mark.skip(
                    reason="REQ-024 ha-websocket runtime " + websocket_error))
    try:
        importlib.import_module("home_device_fabric.ha_health")
        health_error = None
    except ImportError:
        health_error = "absent"
    except Exception:
        health_error = "broken"
    if config.getoption("--require-ha-health-runtime") and health_error:
        raise pytest.UsageError("REQ-026 ha-health runtime required but " + health_error)
    if health_error:
        for item in items:
            if item.path.name == "test_ha_health.py":
                item.add_marker(pytest.mark.skip(
                    reason="REQ-026 ha-health runtime " + health_error))
    try:
        importlib.import_module("home_device_fabric.ha_subscription")
        subscription_error = None
    except ImportError:
        subscription_error = "absent"
    except Exception:
        subscription_error = "broken"
    if config.getoption("--require-ha-subscription-runtime") and subscription_error:
        raise pytest.UsageError(
            "REQ-027 ha-subscription runtime required but " + subscription_error)
    if subscription_error:
        for item in items:
            if item.path.name == "test_ha_subscription.py":
                item.add_marker(pytest.mark.skip(
                    reason="REQ-027 ha-subscription runtime " + subscription_error))
    try:
        importlib.import_module("home_device_fabric.ha_normalization")
        normalization_error = None
    except ImportError:
        normalization_error = "absent"
    except Exception:
        normalization_error = "broken"
    if config.getoption("--require-ha-normalization-runtime") and normalization_error:
        raise pytest.UsageError(
            "REQ-028 ha-normalization runtime required but " + normalization_error)
    if normalization_error:
        for item in items:
            if item.path.name == "test_ha_normalization.py":
                item.add_marker(pytest.mark.skip(
                    reason="REQ-028 ha-normalization runtime " + normalization_error))
    rest = ha_rest_available()
    if config.getoption("--require-ha-rest-runtime") and not rest:
        raise pytest.UsageError("REQ-023 ha-rest runtime required but absent")
    if not rest:
        for item in items:
            if item.path.name == "test_ha_rest.py":
                item.add_marker(pytest.mark.skip(reason="REQ-023 ha-rest runtime absent"))
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
        or session.config.getoption("--require-ha-rest-runtime")
        or session.config.getoption("--require-ha-websocket-runtime")
        or session.config.getoption("--require-ha-health-runtime")
        or session.config.getoption("--require-ha-subscription-runtime")
        or session.config.getoption("--require-ha-normalization-runtime")
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
    if (request.node.get_closest_marker("ha_websocket_async")
            and not request.node.get_closest_marker("ha_websocket_pure")):
        # Fake async tests permit only the loop's monotonic clock and creation
        # of its self-pipe. Wire cases additionally permit numeric-loopback
        # networking, frame entropy and log timestamps. Only the explicit TLS
        # fixture may spawn openssl. No case may use getenv/system/urllib.
        wire = request.node.get_closest_marker("ha_websocket_wire")
        tls = request.node.get_closest_marker("ha_websocket_tls_fixture")
        connect, connect_ex = socket.socket.connect, socket.socket.connect_ex
        resolve, pair = socket.getaddrinfo, socket.socketpair

        def denied(*args, **kwargs):
            attempts.append("ambient")
            raise AssertionError("ambient effect denied")

        def numeric_loopback(address):
            try:
                return ipaddress.ip_address(address[0]).is_loopback
            except (ValueError, TypeError, IndexError):
                return False

        def guarded_connect(sock, address):
            if not wire or not numeric_loopback(address):
                return denied()
            return connect(sock, address)

        def guarded_connect_ex(sock, address):
            if not wire or not numeric_loopback(address):
                return denied()
            return connect_ex(sock, address)

        def guarded_resolve(host, *args, **kwargs):
            if not wire or not numeric_loopback((host,)):
                return denied()
            return resolve(host, *args, **kwargs)

        def infrastructure_pair(*args, **kwargs):
            # Windows implements socketpair with a local TCP connect. This
            # allowance exists only while creating that pair, before user code.
            with monkeypatch.context() as setup:
                setup.setattr(socket.socket, "connect", connect)
                setup.setattr(socket.socket, "connect_ex", connect_ex)
                return pair(*args, **kwargs)

        with monkeypatch.context() as patch:
            for module, names in [
                (time, ("time", "time_ns", "monotonic_ns", "perf_counter",
                        "perf_counter_ns", "process_time", "process_time_ns", "sleep")),
                (random, ("random", "randint", "randrange", "getrandbits")),
                (os, ("getenv", "system", "urandom")),
                (subprocess, ("Popen",)),
                (urllib.request, ("urlopen",)),
                (socket, ("create_connection",)),
            ]:
                for name in names:
                    if wire and (module, name) in (
                        (time, "time"), (time, "time_ns"), (random, "getrandbits"),
                        (os, "urandom"), (socket, "create_connection"),
                    ):
                        continue
                    if tls and module is subprocess:
                        continue
                    patch.setattr(module, name, denied)
            patch.setattr(socket.socket, "connect", guarded_connect)
            patch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
            patch.setattr(socket, "getaddrinfo", guarded_resolve)
            patch.setattr(socket, "socketpair", infrastructure_pair)
            yield attempts
        assert not attempts, "forbidden effects attempted even if swallowed"
        return

    if request.node.get_closest_marker("ha_rest_boundary"):
        # Historical REQ-023 boundary permits ambient effects beyond loopback
        # restrictions; the more precise REQ-024 guard above is separate.
        connect = socket.socket.connect
        connect_ex = socket.socket.connect_ex
        resolve = socket.getaddrinfo

        def loopback(address):
            try:
                return ipaddress.ip_address(address[0]).is_loopback
            except (ValueError, TypeError, IndexError):
                return False

        def guarded_connect(sock, address):
            if not loopback(address):
                attempts.append(address)
                raise AssertionError("non-loopback network denied")
            return connect(sock, address)

        def guarded_connect_ex(sock, address):
            if not loopback(address):
                attempts.append(address)
                raise AssertionError("non-loopback network denied")
            return connect_ex(sock, address)

        def guarded_resolve(host, *args, **kwargs):
            if not loopback((host,)):
                attempts.append(host)
                raise AssertionError("non-loopback DNS denied")
            return resolve(host, *args, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(socket.socket, "connect", guarded_connect)
            patch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
            patch.setattr(socket, "getaddrinfo", guarded_resolve)
            yield attempts
        assert not attempts, "forbidden network attempted even if swallowed"
        return

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
