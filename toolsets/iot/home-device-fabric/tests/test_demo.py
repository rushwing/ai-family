"""Independent REQ-020 oracles exercise packaged fixtures and real caller effects."""

import json
import subprocess
import sys
from copy import deepcopy
from dataclasses import replace

import pytest
from state_schema import action_contracts as actions
from state_schema.initial_capabilities import load_initial_capabilities
from state_schema.provider_contracts import MockConfiguration, NormalizedInput, ProviderError


def runtime():
    from home_device_fabric import caller, scenarios
    return caller, scenarios


def demo(device, scenario):
    return runtime()[0].run_demo(device, scenario)


def values(case, member):
    return [x["record"]["payload"]["value"] for x in case["timeline"]
            if x["kind"] == "state_input" and x["record"]["member"] == member]


@pytest.mark.tc020_01
def test_models_config_registration_and_unknown_snapshots():
    from home_device_fabric import MockProvider
    _, s = runtime()
    assert (s.MockSwitch().device_id, s.MockCurtain().device_id,
            s.MockTemperatureSensor().device_id) == (
                "device-switch", "device-curtain", "device-temperature")
    p = MockProvider(s.configuration())
    assert [r.device_id for r in p.discover()] == [
        "device-switch", "device-curtain", "device-temperature"]
    assert [r.supported_capabilities for r in p.discover()] == [
        (("home.switchable", 1),), (("home.positionable", 1),),
        (("home.temperature_sensor", 1),)]
    for model, scenario in ((s.MockSwitch(), "success"), (s.MockCurtain(), "success"),
                            (s.MockTemperatureSensor(), "observe")):
        assert model.build(scenario) == s.build_scenario(model.device, scenario)
        assert model.registration().device_id == model.device_id
    assert len({r.binding.to_dict()["mapping"]["device_key"] for r in p.discover()}) == 3
    for state in p.snapshot():
        assert state.to_dict()["reported_state"] == {}
        assert state.to_dict()["availability"]["status"] == "unknown"
    descriptors = s.configuration()["catalogue"]["capabilities"]
    assert all(d["events"] == {} and d["capability_version"] == 1 for d in descriptors)


@pytest.mark.tc020_02
@pytest.mark.parametrize("device,member,expected", [
    ("switch", "is_on", [[False, True], [False, False]]),
    ("curtain", "position_percent", [[0, 60, 0], [0, 40, 100], [0, 20, 40]]),
])
def test_success_requires_literal_matching_reports(device, member, expected):
    result = demo(device, "success")
    assert [values(c, member) for c in result["cases"]] == expected
    assert result["dispatch_count"] == len(expected)
    for case, samples in zip(result["cases"], expected):
        assert case["initial_state"]["reported_state"] == {}
        assert case["task"]["state"] == "succeeded"
        assert case["result"]["physical_outcome"] == "confirmed"
        assert case["result"]["evidence"]["state"] == case["final_state"]
        assert case["final_state"]["reported_state"][member]["value"] == samples[-1]
        assert type(case["final_state"]["reported_state"][member]["value"]) is type(samples[-1])
        ack = [t for t in case["timeline"] if t["kind"] == "provider_outcome"]
        assert len(ack) == 1 and ack[0]["time_ms"] == 0 and ack[0]["task_state"] == "running"
        assert case["dispatch_count"] == 1
        if device == "curtain":
            intermediate = next(t for t in case["timeline"] if t["time_ms"] == 5)
            assert intermediate["task_state"] == "running"
            assert intermediate["error"]["code"] == "ineligible_evidence"


@pytest.mark.tc020_02
@pytest.mark.parametrize("device,member,last", [("switch", "is_on", False),
                                               ("curtain", "position_percent", 20)])
def test_mismatch_never_manufactures_completion(device, member, last):
    case = demo(device, "mismatch")["cases"][0]
    assert case["task"]["state"] == "timed_out"
    assert case["final_state"]["reported_state"][member]["value"] == last
    assert case["result"]["physical_outcome"] == "unverified"


@pytest.mark.tc020_03
def test_temperature_read_only_celsius_zero_negative_positive():
    result = demo("temperature", "observe")
    case = result["cases"][0]
    assert values(case, "temperature_c") == [0, -5.5, 21.25]
    assert case["task"] is None and case["result"] is None
    assert case["dispatch_count"] == result["dispatch_count"] == 0
    descriptor = result["capabilities"][0]
    assert descriptor["actions"] == {}
    assert result["units"] == {"temperature_c": "degrees_celsius"}
    assert descriptor["properties"]["temperature_c"]["read_only"] is True


@pytest.mark.tc020_03
@pytest.mark.parametrize("device,member,known", [
    ("switch", "is_on", False), ("curtain", "position_percent", 0),
    ("temperature", "temperature_c", 0),
])
def test_offline_keeps_unknown_and_known_separate(device, member, known):
    result = demo(device, "offline")
    unknown, present = result["cases"]
    assert unknown["final_state"]["reported_state"] == {}
    assert present["final_state"]["reported_state"][member]["value"] == known
    assert type(present["final_state"]["reported_state"][member]["value"]) is type(known)
    for case in (unknown, present):
        assert case["final_state"]["availability"]["status"] == "offline"
        assert case["task"] is None and case["dispatch_count"] == 0
        if device != "temperature":
            assert case["rejection"] == {"code": "offline", "source": "caller"}


@pytest.mark.tc020_03
@pytest.mark.parametrize("device,scenario,count", [
    ("curtain", "invalid-position", 4), ("temperature", "write-rejected", 1),
    ("switch", "malformed", 4),
])
def test_real_shared_request_validation_no_dispatch(device, scenario, count, monkeypatch):
    calls = []
    original = actions.create_task

    def tracked(*args, **kwargs):
        calls.append(args[0])
        return original(*args, **kwargs)

    monkeypatch.setattr(actions, "create_task", tracked)
    result = demo(device, scenario)
    assert len(calls) == len(result["cases"]) == count
    assert result["dispatch_count"] == 0
    for case in result["cases"]:
        assert case["rejection"] == {"code": "invalid_request", "source": "action"}
        assert case["task"] is None and case["dispatches"] == []


@pytest.mark.tc020_03
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), True, "0"])
def test_nonfinite_or_malformed_sensor_report_rejects(value):
    _, s = runtime()
    raw = deepcopy(s.build_scenario("temperature", "observe")[0].observations[0][1])
    raw["payload"]["value"] = value
    with pytest.raises(ProviderError):
        NormalizedInput.from_dict(raw, configuration=MockConfiguration.from_dict(s.configuration()))


@pytest.mark.tc020_04
@pytest.mark.parametrize("device,deadline", [("switch", 30000), ("curtain", 120000)])
@pytest.mark.parametrize("scenario", ["timeout", "stale", "wrong-epoch", "deadline-tie", "late"])
def test_ack_provenance_ties_and_late_terminal_immutability(device, deadline, scenario):
    case = demo(device, scenario)["cases"][0]
    assert case["task"]["state"] == "timed_out"
    assert case["result"]["error"] == {"code": "provider_timeout"}
    assert case["result"]["physical_outcome"] == "unverified"
    times = [t["time_ms"] for t in case["timeline"]]
    assert times == sorted(times)
    timeout = next(t for t in case["timeline"] if t["kind"] == "provider_outcome"
                   and t["record"]["result"]["state"] == "timed_out")
    assert timeout["time_ms"] == deadline
    if scenario in ("deadline-tie", "late"):
        at_deadline = case["timeline"].index(timeout)
        assert case["timeline"][at_deadline + 1]["kind"] == "state_input"
        assert case["timeline"][at_deadline + 1]["task_state"] == "timed_out"
        assert case["final_state"] != timeout["state"]
    if scenario in ("stale", "wrong-epoch"):
        assert any(t["error"] and t["error"]["code"] == "rejected_state"
                   for t in case["timeline"])


@pytest.mark.tc020_04
def test_large_jump_and_repeated_advance_settlement(monkeypatch):
    from home_device_fabric import MockProvider
    caller, s = runtime()
    calls = []
    settle = MockProvider.settle

    def tracked(self, task):
        calls.append(task["state"])
        return settle(self, task)

    monkeypatch.setattr(MockProvider, "settle", tracked)
    case = caller.execute_case(s.build_scenario("switch", "success")[0], advance_to_ms=1_000_000)
    assert calls == ["succeeded"]
    assert [t["time_ms"] for t in case["timeline"]][-1] == 10
    assert case["task"]["state"] == "succeeded"


@pytest.mark.tc020_04
def test_offline_evidence_after_dispatch_cannot_confirm():
    caller, s = runtime()
    case = s.build_scenario("switch", "success")[0]
    offline = deepcopy(case.initial_inputs[0])
    offline["payload"].update(status="offline", ordering={"epoch": 1, "sequence": 2})
    altered = replace(case, deliveries=(
        {"delay_ms": 5, "input": offline, "outcome": None}, *case.deliveries),
        expected_task="timed_out")
    result = caller.execute_case(altered)
    assert result["task"]["state"] == "timed_out"
    assert result["final_state"]["reported_state"]["is_on"]["value"] is True
    assert result["final_state"]["availability"]["status"] == "offline"


@pytest.mark.tc020_05
@pytest.mark.cli_boundary
@pytest.mark.parametrize("device,scenario", [
    ("switch", "success"), ("curtain", "success"), ("temperature", "observe"),
    ("switch", "timeout"), ("switch", "offline"),
    ("curtain", "invalid-position"), ("temperature", "write-rejected"),
])
def test_cli_fresh_process_exact_text_and_optimized(device, scenario, tmp_path):
    command = [sys.executable, "-m", "home_device_fabric.demo",
               "--device", device, "--scenario", scenario]
    first = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True)
    second = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True)
    optimized = subprocess.run([sys.executable, "-O", *command[1:]], cwd=tmp_path,
                               capture_output=True, text=True)
    assert first.returncode == second.returncode == optimized.returncode == 0
    assert first.stderr == second.stderr == optimized.stderr == ""
    assert first.stdout == second.stdout == optimized.stdout
    data = json.loads(first.stdout)
    assert first.stdout == json.dumps(data, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False) + "\n"
    assert data.keys() == {"schema_version", "simulation", "device", "scenario", "discovery",
                           "capabilities", "units", "cases", "dispatch_count", "verified"}
    assert data["schema_version"] == 1 and data["simulation"] is True
    assert len(data["discovery"]) == 3
    identity = {"switch": "home.switchable", "curtain": "home.positionable",
                "temperature": "home.temperature_sensor"}[device]
    assert data["capabilities"] == [
        d.to_dict() for d in load_initial_capabilities().capabilities
        if (d.capability_id, d.capability_version) == (identity, 1)
    ]
    assert all(d["events"] == {} for d in data["capabilities"])
    if scenario == "success":
        assert all(c["task"]["state"] == "succeeded" for c in data["cases"])
    elif scenario == "timeout":
        assert data["cases"][0]["task"]["state"] == "timed_out"
    elif scenario == "observe":
        assert data["cases"][0]["final_state"]["reported_state"]["temperature_c"]["value"] == 21.25
    else:
        assert data["dispatch_count"] == 0
        assert all(c["rejection"] is not None for c in data["cases"])


@pytest.mark.tc020_05
@pytest.mark.cli_boundary
@pytest.mark.parametrize("args", [[], ["--device", "secret-value"],
    ["--device", "switch", "--scenario", "secret-value"],
    ["--device", "temperature", "--scenario", "success"],
    ["--device", "switch", "--scenario", "success", "--secret-value"],
    ["--dev", "switch", "--scenario", "success"],
])
def test_cli_errors_are_value_free(args, tmp_path):
    run = subprocess.run([sys.executable, "-m", "home_device_fabric.demo", *args],
                         cwd=tmp_path, capture_output=True, text=True)
    assert run.returncode == 2 and run.stdout == ""
    assert run.stderr in ("demo: unsupported arguments\n", "demo: unsupported device/scenario\n")


@pytest.mark.tc020_05
@pytest.mark.parametrize("code,exit_code", [("expectation_failed", 1), ("unexpected", 1)])
def test_cli_internal_failure_hides_values(code, exit_code, monkeypatch, capsys):
    from home_device_fabric import demo as cli
    _, s = runtime()

    def fail(*args):
        if code == "unexpected":
            raise RuntimeError("private-path private-value")
        raise s.DemoError(code)

    monkeypatch.setattr(cli, "run_demo", fail)
    assert cli.main(["--device", "switch", "--scenario", "success"]) == exit_code
    out, err = capsys.readouterr()
    assert out == "" and "private" not in err


@pytest.mark.tc020_05
@pytest.mark.cli_boundary
def test_optimized_expectation_checks_cannot_disappear(tmp_path):
    code = '''from dataclasses import replace
from home_device_fabric.scenarios import build_scenario
from home_device_fabric.caller import execute_case
execute_case(replace(build_scenario("switch", "success")[0], expected_task="timed_out"))
'''
    result = subprocess.run([sys.executable, "-O", "-c", code], cwd=tmp_path,
                            capture_output=True, text=True)
    assert result.returncode != 0 and "expectation_failed" in result.stderr


@pytest.mark.tc020_06
def test_mutation_isolation_and_reports_independent_of_intent():
    caller, s = runtime()
    baseline = caller.canonical_json(demo("switch", "success"))
    config = s.configuration()
    config["inventory"]["devices"][0]["name"] = "changed"
    assert s.configuration()["inventory"]["devices"][0]["name"] == "device-switch"
    case = s.build_scenario("switch", "success")[0]
    case.request["arguments"]["is_on"] = False
    case = replace(case, expected_task="timed_out")
    result = caller.execute_case(case)
    assert result["final_state"]["reported_state"]["is_on"]["value"] is True
    result["final_state"]["reported_state"]["is_on"]["value"] = "mutated"
    assert caller.canonical_json(demo("switch", "success")) == baseline


@pytest.mark.tc020_06
def test_runtime_file_environment_datetime_denial(monkeypatch):
    import builtins
    import datetime
    import io
    import os
    from collections.abc import Mapping

    caller, s = runtime()
    config = s.configuration()  # Explicit fixed packaged resource loading precedes I/O denial.
    case = s.build_scenario("curtain", "success")[2]
    attempts = []

    def deny(*args, **kwargs):
        attempts.append(1)
        raise AssertionError("ambient access forbidden")

    class DeniedEnvironment(Mapping):
        __getitem__ = deny
        __iter__ = deny
        __len__ = deny

    class DeniedDatetime(datetime.datetime):
        now = classmethod(deny)
        utcnow = classmethod(deny)
        today = classmethod(deny)

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", deny)
        patch.setattr(io, "open", deny)
        patch.setattr(os, "environ", DeniedEnvironment())
        patch.setattr(datetime, "datetime", DeniedDatetime)
        result = caller.execute_case(case, configuration_data=config)
        caller.canonical_json(result)
    assert result["task"]["state"] == "succeeded" and attempts == []


@pytest.mark.tc020_06
def test_required_demo_gate_and_skip_failure(monkeypatch):
    from types import SimpleNamespace

    import conftest

    monkeypatch.setattr(conftest, "demo_available", lambda: False)
    required = SimpleNamespace(getoption=lambda name: name == "--require-demo-runtime")
    with pytest.raises(pytest.UsageError, match="demo runtime required but absent"):
        conftest.pytest_collection_modifyitems(required, [])
    reporter = SimpleNamespace(stats={"skipped": [object()]})
    session = SimpleNamespace(config=SimpleNamespace(
        getoption=required.getoption,
        pluginmanager=SimpleNamespace(getplugin=lambda name: reporter)), exitstatus=0)
    conftest.pytest_sessionfinish(session, 0)
    assert session.exitstatus == pytest.ExitCode.TESTS_FAILED


@pytest.mark.tc020_03
@pytest.mark.parametrize("arguments", [{}, {"is_on": True, "extra": False}, [], None])
def test_malformed_switch_argument_shapes_reject(arguments):
    caller, s = runtime()
    case = s.build_scenario("switch", "success")[0]
    case.request["arguments"] = arguments
    output = caller.execute_case(replace(case, expected_task=None,
                                         expected_rejection="invalid_request"))
    assert output["task"] is None and output["dispatch_count"] == 0
    assert output["rejection"] == {"code": "invalid_request", "source": "action"}


@pytest.mark.tc020_01
@pytest.mark.parametrize("device,scenario,identity", [
    ("switch", "success", "home.switchable"),
    ("curtain", "success", "home.positionable"),
    ("temperature", "observe", "home.temperature_sensor"),
])
def test_output_descriptors_match_exact_canonical_revision(device, scenario, identity):
    output = demo(device, scenario)
    expected = [d.to_dict() for d in load_initial_capabilities().capabilities
                if (d.capability_id, d.capability_version) == (identity, 1)]
    assert len(expected) == 1
    assert output["capabilities"] == expected
    assert output["capabilities"][0]["events"] == {}


@pytest.mark.tc020_01
def test_output_selects_exact_revision_when_catalogue_has_multiple(monkeypatch):
    caller, s = runtime()
    config = s.configuration()
    original = next(d for d in config["catalogue"]["capabilities"]
                    if d["capability_id"] == "home.switchable")
    other = deepcopy(original)
    other["capability_version"] = 2
    config["catalogue"]["capabilities"].append(other)
    monkeypatch.setattr(caller, "configuration", lambda: deepcopy(config))
    output = caller.run_demo("switch", "success")
    assert output["capabilities"] == [original]
    assert output["discovery"][0]["supported_capabilities"] == [
        {"capability_id": "home.switchable", "capability_version": 1}]


@pytest.mark.tc020_04
@pytest.mark.parametrize("scenario", ["success", "timeout"])
def test_caller_rejects_provider_duplicate_delivery_on_readvance(monkeypatch, scenario):
    caller, s = runtime()
    actual_provider = caller.MockProvider
    instances = []

    class ReplayingProvider(actual_provider):
        def __init__(self, config):
            super().__init__(config)
            self.saved = None
            self.advancements = 0
            instances.append(self)

        def advance(self, horizon):
            self.advancements += 1
            if self.advancements == 2:
                yield self.saved
                return
            for delivery in super().advance(horizon):
                self.saved = delivery
                yield delivery

    # Inject the regression at the provider boundary while retaining real first-run
    # scheduling, shared State/Action validation and terminal settlement.
    monkeypatch.setattr(caller, "MockProvider", ReplayingProvider)
    with pytest.raises(s.DemoError, match="^expectation_failed$"):
        caller.execute_case(s.build_scenario("switch", scenario)[0])
    assert instances[-1].advancements == 2 and instances[-1].saved is not None
    assert len(instances[-1].dispatch_log) == 1
