"""Independent REQ-021 acceptance; do not trust a runner's passed verdict alone."""

import hashlib
import json
import subprocess
import sys
import time
from copy import deepcopy
from pathlib import Path

import pytest

EXPECTED_IDS = (
    "discovery",
    "catalogue",
    "provider-binding",
    "provider-arguments",
    "provider-accepted",
    "provider-support",
    "provider-attempt",
    "provider-action",
    "provider-revision",
    "switch-on",
    "switch-off",
    "curtain-closed",
    "curtain-open",
    "curtain-partial",
    "switch-timeout",
    "switch-mismatch",
    "switch-stale",
    "switch-wrong-epoch",
    "switch-deadline-tie",
    "switch-late",
    "curtain-timeout",
    "curtain-mismatch",
    "curtain-stale",
    "curtain-wrong-epoch",
    "curtain-deadline-tie",
    "curtain-late",
    "switch-failed",
    "curtain-failed",
    "switch-offline-unknown",
    "switch-offline-known",
    "curtain-offline-unknown",
    "curtain-offline-known",
    "temperature-offline-unknown",
    "temperature-offline-known",
    "switch-invalid-0",
    "switch-invalid-1",
    "switch-invalid-2",
    "switch-invalid-3",
    "curtain-invalid-0",
    "curtain-invalid-1",
    "curtain-invalid-2",
    "curtain-invalid-3",
    "request-action",
    "request-member",
    "request-revision",
    "temperature-observe",
    "temperature-write",
    "replay",
    "conflict",
    "replay-invalid-type",
    "provider-ordering",
)
HASH = "0cb57579e3eb82bb1d7c73722f1c5e3c386427d45c7efde9ed011a5c7f18e6bd"
_SLEEP = time.sleep


def runtime():
    from home_device_fabric import conformance

    return conformance


@pytest.fixture(scope="module")
def report():
    return runtime().run_conformance()


def by_id(report, name):
    return next(c["evidence"] for c in report["cases"] if c["case_id"] == name)


@pytest.mark.tc021_01
def test_inventory_factory_is_used_and_records_are_independent(report):
    from conformance_wrappers import factory

    calls = []
    wrapper = factory()

    def tracked(data):
        calls.append(deepcopy(data))
        return wrapper(data)

    r = runtime().run_conformance(tracked)
    # Discovery constructs twice; the caller catalogue check needs no provider.
    assert r == report and len(calls) == 51
    assert [c["case_id"] for c in r["cases"]] == list(EXPECTED_IDS)
    assert r["counts"] == {"total": 51, "executed": 51, "passed": 51, "failed": 0, "skipped": 0}
    assert r["inventory_sha256"] == HASH and r["inventory_version"] == 1
    assert r["profile"] == "offline-provider-v1"
    assert (
        hashlib.sha256(runtime().canonical_json(r["expected_cases"]).encode()).hexdigest() == HASH
    )
    assert runtime().validate_report(r)
    discovery = by_id(r, "discovery")["discovery"]
    assert [d["device_id"] for d in discovery] == [
        "device-switch",
        "device-curtain",
        "device-temperature",
    ]
    assert [d["supported_capabilities"] for d in discovery] == [
        [{"capability_id": x, "capability_version": 1}]
        for x in ("home.switchable", "home.positionable", "home.temperature_sensor")
    ]
    for state in by_id(r, "discovery")["snapshots"]:
        assert state["availability"]["status"] == "unknown" and state["reported_state"] == {}
    assert any(c["scenarios"] for c in calls)


@pytest.mark.tc021_02
@pytest.mark.parametrize(
    "name,code",
    [
        ("binding", "binding_mismatch"),
        ("arguments", "invalid_task"),
        ("accepted", "invalid_task"),
        ("support", "unsupported"),
        ("attempt", "invalid_attempt"),
        ("action", "invalid_task"),
        ("revision", "invalid_task"),
    ],
)
def test_provider_rejections_are_real_and_effect_free(report, name, code):
    assert by_id(report, "provider-" + name) == {
        "rejection": code,
        "dispatches": [],
        "deliveries": [],
    }


@pytest.mark.tc021_02
def test_exact_catalogue_sensor_samples_and_provider_ordering(report):
    from state_schema.initial_capabilities import load_initial_capabilities

    descriptors = by_id(report, "catalogue")["descriptors"]
    assert descriptors == [d.to_dict() for d in load_initial_capabilities().capabilities[:3]]
    assert descriptors[2]["actions"] == {} and descriptors[2]["events"] == {}
    assert descriptors[2]["properties"]["temperature_c"]["read_only"] is True
    assert descriptors[1]["properties"]["position_percent"]["value_schema"] == {
        "type": "integer",
        "minimum": 0,
        "maximum": 100,
    }
    sensor = by_id(report, "temperature-observe")
    assert sensor["task"] is None and sensor["dispatches"] == []
    assert [
        x["record"]["payload"]["value"]
        for x in sensor["timeline"]
        if x["record"]["kind"] == "property"
    ] == [0, -5.5, 21.25]
    assert by_id(report, "provider-ordering")["snapshot"]["reported_state"]["is_on"] == {
        "status": "known",
        "value": False,
        "observed_at": "2026-01-01T00:00:00Z",
        "ordering": {"epoch": 1, "sequence": 2},
    }


@pytest.mark.tc021_03
@pytest.mark.parametrize(
    "name,value",
    [
        ("switch-on", True),
        ("switch-off", False),
        ("curtain-closed", 0),
        ("curtain-open", 100),
        ("curtain-partial", 40),
    ],
)
def test_independent_action_values_and_timeline(report, name, value):
    actual = by_id(report, name)
    assert len(actual["dispatches"]) == 1 and actual["repeated"] == []
    assert actual["task"]["state"] == "succeeded"
    assert actual["task"]["result"]["physical_outcome"] == "confirmed"
    member = "is_on" if name.startswith("switch") else "position_percent"
    reported = actual["final_state"]["reported_state"][member]["value"]
    assert type(reported) is type(value) and reported == value
    ack = next(x for x in actual["timeline"] if x["kind"] == "outcome")
    assert ack["time_ms"] == 0 and ack["task_state"] == "running"
    if name.startswith("curtain"):
        assert next(x for x in actual["timeline"] if x["time_ms"] == 5)["task_state"] == "running"
    assert actual["task"]["result"]["evidence"]["state"] == actual["final_state"]


@pytest.mark.tc021_03
@pytest.mark.parametrize("device,deadline", [("switch", 30000), ("curtain", 120000)])
@pytest.mark.parametrize(
    "name", ["timeout", "mismatch", "stale", "wrong-epoch", "deadline-tie", "late"]
)
def test_deadlines_provenance_and_terminal_states(report, device, deadline, name):
    actual = by_id(report, device + "-" + name)
    assert actual["task"]["state"] == "timed_out"
    assert actual["task"]["result"]["physical_outcome"] == "unverified"
    assert actual["task"]["result"]["error"] == {"code": "provider_timeout"}
    assert [x["time_ms"] for x in actual["timeline"] if x["kind"] == "outcome"] == [0, deadline]
    assert actual["repeated"] == []
    if name in ("stale", "wrong-epoch"):
        assert next(x for x in actual["timeline"] if x["time_ms"] == 10)["applied"] is False
        expected = False if device == "switch" else 0
        member = "is_on" if device == "switch" else "position_percent"
        value = actual["final_state"]["reported_state"][member]["value"]
        assert type(value) is type(expected) and value == expected
    if name == "deadline-tie":
        at_deadline = [x for x in actual["timeline"] if x["time_ms"] == deadline]
        assert [x["kind"] for x in at_deadline] == ["outcome", "input"]
        assert all(x["task_state"] == "timed_out" for x in at_deadline)


@pytest.mark.tc021_03
@pytest.mark.parametrize("device", ["switch", "curtain"])
def test_scripted_failure_does_not_establish_physical_success(report, device):
    actual = by_id(report, device + "-failed")
    assert actual["task"]["state"] == "failed"
    assert actual["task"]["result"]["physical_outcome"] == "unverified"
    assert actual["task"]["result"]["error"] == {"code": "scripted_failure"}
    assert actual["repeated"] == []


@pytest.mark.tc021_04
@pytest.mark.parametrize("device", ["switch", "curtain", "temperature"])
@pytest.mark.parametrize("known", [True, False])
def test_offline_never_becomes_false_or_zero(report, device, known):
    actual = by_id(report, device + "-offline-" + ("known" if known else "unknown"))
    assert actual["dispatches"] == [] and actual["task"] is None
    assert actual["final_state"]["availability"]["status"] == "offline"
    reported = actual["final_state"]["reported_state"]
    if known:
        expected = False if device == "switch" else 0
        value = next(iter(reported.values()))["value"]
        assert type(value) is type(expected) and value == expected
    else:
        assert reported == {}
    assert actual["rejection"] == (None if device == "temperature" else "offline")


@pytest.mark.tc021_04
@pytest.mark.parametrize(
    "name,verdict",
    [("replay", "replay"), ("conflict", "conflict"), ("replay-invalid-type", "invalid")],
)
def test_real_caller_replay_classification_suppresses_effects(report, name, verdict):
    actual = by_id(report, name)
    assert actual["verdict"] == verdict and len(actual["dispatches"]) == 1
    assert actual["dispatches"][0]["task_id"] == actual["original_task"]["task_id"]


@pytest.mark.tc021_04
@pytest.mark.parametrize(
    "name",
    [
        *(f"switch-invalid-{i}" for i in range(4)),
        *(f"curtain-invalid-{i}" for i in range(4)),
        "request-action",
        "request-member",
        "request-revision",
        "temperature-write",
    ],
)
def test_caller_schema_errors_never_dispatch(report, name):
    actual = by_id(report, name)
    assert actual["rejection"] == "invalid_request"
    assert actual["task"] is None and actual["dispatches"] == []


@pytest.mark.tc021_05
@pytest.mark.parametrize(
    "defect,failed_id",
    [
        ("identity", "discovery"),
        ("support", "discovery"),
        ("ack", "switch-on"),
        ("mismatch", "switch-mismatch"),
        ("tie", "switch-deadline-tie"),
        ("repeat", "switch-on"),
        ("policy", "replay"),
    ],
)
def test_same_checks_detect_defects_behind_injected_seam(defect, failed_id):
    from conformance_wrappers import factory

    r = runtime().run_conformance(factory(defect))
    case = next(c for c in r["cases"] if c["case_id"] == failed_id)
    assert case["executed"] is True and case["status"] == "failed" and case["error"]
    assert r["passed"] is False and r["counts"]["failed"] > 0
    assert not runtime().validate_report(r)


@pytest.mark.tc021_05
@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "duplicate",
        "extra",
        "expected",
        "hash",
        "version",
        "count",
        "bool-count",
        "skipped",
        "failed",
        "unexecuted",
        "nonfinite",
        "extra-field",
        "tuple",
        "empty-evidence",
    ],
)
def test_report_verifier_rejects_incomplete_or_altered_reports(report, mutation):
    r = deepcopy(report)
    if mutation == "missing":
        r["cases"].pop()
    elif mutation == "duplicate":
        r["cases"][-1] = r["cases"][0]
    elif mutation == "extra":
        r["cases"].append(r["cases"][0])
    elif mutation == "expected":
        r["expected_cases"].pop()
    elif mutation in ("hash", "version"):
        r["inventory_" + ("sha256" if mutation == "hash" else "version")] = "changed"
    elif mutation in ("count", "bool-count"):
        r["counts"]["failed"] = True if mutation == "bool-count" else 1
    elif mutation in ("skipped", "failed"):
        r["cases"][0]["status"] = mutation
    elif mutation == "unexecuted":
        r["cases"][0]["executed"] = False
    elif mutation == "nonfinite":
        r["cases"][0]["evidence"]["value"] = float("nan")
    elif mutation == "extra-field":
        r["secret"] = "not allowed"
    elif mutation == "tuple":
        r["cases"][0]["evidence"]["tuple"] = (1,)
    elif mutation == "empty-evidence":
        r["cases"][0]["evidence"] = {}
    assert not runtime().validate_report(r)


@pytest.mark.tc021_05
def test_truncated_runner_inventory_and_factory_failure_cannot_pass(monkeypatch):
    c = runtime()
    monkeypatch.setattr(c, "CASES", c.CASES[:-1])
    truncated = c.run_conformance()
    assert truncated["passed"] is False and not c.validate_report(truncated)

    def broken(data):
        raise RuntimeError("supplied-private-value")

    failed = c.run_conformance(broken)
    assert failed["passed"] is False and failed["counts"]["failed"] > 0
    assert "supplied-private-value" not in c.canonical_json(failed)


@pytest.mark.tc021_06
@pytest.mark.cli_boundary
def test_cli_repeated_optimized_reports_and_invalid_arguments(monkeypatch):
    def invoke(args):
        # subprocess may sleep while reaping; permit that explicit boundary only.
        with monkeypatch.context() as patch:
            patch.setattr(time, "sleep", _SLEEP)
            return subprocess.run(args, capture_output=True, text=True, timeout=30)

    command = [sys.executable, "-I", "-m", "home_device_fabric.conformance"]
    first = invoke(command)
    repeat = invoke(command)
    optimized = invoke([sys.executable, "-O", *command[1:]])
    assert first.returncode == repeat.returncode == optimized.returncode == 0
    assert first.stderr == repeat.stderr == optimized.stderr == ""
    assert first.stdout == repeat.stdout == optimized.stdout
    r = json.loads(first.stdout)
    assert [c["case_id"] for c in r["cases"]] == list(EXPECTED_IDS)
    assert r["counts"]["passed"] == 51 and r["inventory_sha256"] == HASH
    assert first.stdout == runtime().canonical_json(r) + "\n"
    bad = invoke([*command, "--private-value"])
    assert bad.returncode == 2 and bad.stdout == "" and bad.stderr == "invalid_arguments\n"


@pytest.mark.tc021_06
def test_runtime_avoids_io_and_ambient_effects(monkeypatch):
    import builtins
    import datetime
    import io
    import os

    import state_schema

    c = runtime()
    from home_device_fabric.scenarios import configuration

    configuration()
    resource = Path(state_schema.__file__).parent / "initial_capabilities.v1.json"
    real_io_open = io.open
    attempts = []

    def deny(*args, **kwargs):
        attempts.append(1)
        raise AssertionError("ambient effect")

    def resource_only(path, mode="r", *args, **kwargs):
        if Path(path) != resource or mode not in ("r", "rb"):
            return deny()
        return real_io_open(path, mode, *args, **kwargs)

    class NoEnvironment:
        __getitem__ = deny
        __iter__ = deny
        __len__ = deny
        get = deny

    class NoClock:
        now = staticmethod(deny)
        utcnow = staticmethod(deny)
        today = staticmethod(deny)

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", deny)
        patch.setattr(io, "open", resource_only)
        patch.setattr(os, "open", deny)
        patch.setattr(os, "environ", NoEnvironment())
        patch.setattr(datetime, "datetime", NoClock)
        r = c.run_conformance()
    assert r["passed"] and not attempts


@pytest.mark.tc021_05
def test_cli_failure_is_exit_one_and_failure_diagnostics_are_fixed(monkeypatch, capsys):
    c = runtime()
    failed = c.run_conformance(lambda data: None)
    assert not failed["passed"]
    assert all(x["error"] == "setup_failed" for x in failed["cases"] if x["case_id"] != "catalogue")
    monkeypatch.setattr(c, "run_conformance", lambda: failed)
    monkeypatch.setattr(sys, "argv", ["conformance"])
    assert c.main() == 1
    captured = capsys.readouterr()
    assert captured.err == "" and captured.out == c.canonical_json(failed) + "\n"


@pytest.mark.tc021_05
def test_nonfinite_driver_evidence_still_emits_finite_failed_report():
    from types import SimpleNamespace

    from conformance_wrappers import Forward
    from home_device_fabric.conformance import ConformanceDriver

    class Nonfinite(Forward):
        def snapshot(self):
            states = []
            for state in super().snapshot():
                raw = state.to_dict()
                raw["desired_state"] = float("nan")
                states.append(
                    SimpleNamespace(device_id=state.device_id, to_dict=lambda raw=raw: raw)
                )
            return tuple(states)

    r = runtime().run_conformance(lambda data: ConformanceDriver(Nonfinite(data)))
    assert not r["passed"] and not runtime().validate_report(r)
    assert "NaN" not in runtime().canonical_json(r)
    assert any(c["evidence"] == {"diagnostic": "invalid_evidence"} for c in r["cases"])
