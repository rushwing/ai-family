"""Offline caller projection and adjudication using the existing shared contracts."""

from __future__ import annotations

import json
from typing import cast

from state_schema import action_contracts as actions
from state_schema.canonical_state import StateError, apply_state_update
from state_schema.provider_contracts import MockConfiguration, NormalizedInput, json_snapshot

from .mock import MockProvider
from .scenarios import HOME, MODELS, DemoCase, DemoError, Json, build_scenario, configuration


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _copy(value: Json) -> Json:
    return cast(Json, json_snapshot(value))


def _evidence(task: Json, kind: str) -> Json:
    return {
        "kind": kind, "task_id": task["task_id"], "trace_id": task["trace_id"],
        **{k: task["request"][k] for k in
           ("home_id", "device_id", "capability_id", "capability_version", "action_id")},
    }


def _result(task: Json, state: str, evidence: Json | None = None) -> Json:
    return {
        "schema_version": 1, "task_id": task["task_id"], "trace_id": task["trace_id"],
        **{k: task["request"][k] for k in
           ("home_id", "device_id", "capability_id", "capability_version", "action_id")},
        "state": state, "output": {"present": False, "value": None}, "error": None,
        "evidence": evidence, "physical_outcome": "confirmed" if state == "succeeded"
        else "unverified",
    }


def execute_case(case: DemoCase, *, configuration_data: object = None,
                 advance_to_ms: int | None = None) -> Json:
    """Run one isolated case; optional explicit config/horizon support reuse and tests."""
    config = MockConfiguration.from_dict(
        configuration() if configuration_data is None else json_snapshot(configuration_data)
    )
    data = config.to_dict()
    model = MODELS[case.device]
    provider = MockProvider(data)
    state: Json = next(s.to_dict() for s in provider.snapshot() if s.device_id == model.device_id)
    initial = _copy(state)
    timeline: list[Json] = []
    task: Json | None = None
    rejection: Json | None = None

    def record(time_ms: int, kind: str, item: Json, error: Json | None = None) -> None:
        timeline.append({
            "time_ms": time_ms, "kind": kind, "record": _copy(item), "state": _copy(state),
            "task_state": None if task is None else task["state"], "error": error,
        })

    def observe(raw: Json, time_ms: int) -> None:
        nonlocal state, task
        inp = NormalizedInput.from_dict(raw, configuration=config).to_dict()
        error = None
        applied = True
        try:
            state = apply_state_update(
                state, current_epoch=1,
                reported_state={inp["member"]: inp["payload"]}
                if inp["kind"] == "property" else None,
                availability=inp["payload"] if inp["kind"] == "availability" else None,
            )
        except StateError:
            applied = False
            error = {"code": "rejected_state", "source": "state"}
        if applied and task is not None and task["state"] == "running" and inp["correlation"]:
            evidence = {**_evidence(task, "state"), "state": state}
            try:
                task = actions.transition_task(
                    task, _result(task, "succeeded", evidence),
                    inventory=data["inventory"], catalogue=data["catalogue"],
                )
            except actions.ActionError:
                error = {"code": "ineligible_evidence", "source": "action"}
            else:
                provider.settle(task)
        record(time_ms, "state_input", inp, error)

    for inp in case.initial_inputs:
        observe(inp, 0)
    ready = _copy(state)
    if case.request is not None:
        requester = {"subject_id": "subject-demo", "family_member_id": "member-demo",
                     "home_id": HOME, "role": "adult"}
        try:
            # Real shared validation is the only request admission path.
            accepted = actions.create_task(
                case.request, requester=requester, task_id=case.task_id,
                inventory=data["inventory"], catalogue=data["catalogue"],
            )
        except actions.ActionError:
            rejection = {"code": "invalid_request", "source": "action"}
        else:
            # Caller policy; MockProvider.submit itself retains its frozen semantics.
            if state["availability"]["status"] == "offline":
                rejection = {"code": "offline", "source": "caller"}
            else:
                task = actions.transition_task(
                    accepted, _result(accepted, "running"),
                    inventory=data["inventory"], catalogue=data["catalogue"],
                    dispatch_context={"current_epoch": 1,
                                      "baseline": {"epoch": 1, "sequence": 1}},
                )
                ack = {"schema_version": 1, "provider": "mock",
                       "provider_instance_id": data["provider_instance_id"],
                       "result": _result(task, "running", _evidence(task, "ack"))}
                data["scenarios"] = [{
                    "task_id": case.task_id, "attempt_id": "attempt-demo",
                    "deliveries": [{"delay_ms": 0, "input": None, "outcome": ack},
                                   *case.deliveries],
                }]
                # Rebuild after the complete script is known: REQ-019 freezes scenarios
                # at construction. Preserve caller State; provider snapshots start unknown.
                provider = MockProvider(data)
                binding = next(r.binding.to_dict() for r in provider.discover()
                               if r.device_id == model.device_id)
                provider.submit(task, binding=binding, attempt_id="attempt-demo")
                record(0, "dispatch", provider.dispatch_log[0])
                horizon = case.horizon_ms if advance_to_ms is None else advance_to_ms
                # Consume chronologically and settle between yields, even on large jumps.
                for delivery in provider.advance(horizon):
                    if delivery.input is not None:
                        observe(delivery.input.to_dict(), delivery.time_ms)
                    elif delivery.outcome is not None:
                        outcome: Json = delivery.outcome.to_dict()
                        result = outcome["result"]
                        if task is not None and task["state"] == "running":
                            if result["state"] == "running":
                                actions.validate_result(
                                    result, task=task, inventory=data["inventory"],
                                    catalogue=data["catalogue"],
                                )
                            else:
                                task = actions.transition_task(
                                    task, result, inventory=data["inventory"],
                                    catalogue=data["catalogue"],
                                )
                                provider.settle(task)
                        record(delivery.time_ms, "provider_outcome", outcome)
                if list(provider.advance(horizon)):
                    raise DemoError("expectation_failed")
    for time_ms, inp in case.observations:
        observe(inp, time_ms)
    actual_task = None if task is None else task["state"]
    actual_rejection = None if rejection is None else rejection["code"]
    expected_dispatches = 1 if case.request is not None and case.expected_rejection is None else 0
    if (actual_task != case.expected_task or actual_rejection != case.expected_rejection
            or len(provider.dispatch_log) != expected_dispatches):
        raise DemoError("expectation_failed")
    return {
        "name": case.name, "initial_state": initial, "ready_state": ready,
        "final_state": state, "timeline": timeline, "task": task,
        "result": None if task is None else task["result"], "rejection": rejection,
        "dispatches": list(provider.dispatch_log), "dispatch_count": len(provider.dispatch_log),
    }


def run_demo(device: str, scenario: str) -> Json:
    cases = build_scenario(device, scenario)
    data = configuration()
    provider = MockProvider(data)
    results = [execute_case(case, configuration_data=data) for case in cases]
    selected = MODELS[device]
    descriptors = data["catalogue"]["capabilities"]
    return {
        "schema_version": 1, "simulation": True, "device": device, "scenario": scenario,
        "discovery": [r.to_dict() for r in provider.discover()],
        "capabilities": [d for d in descriptors
                         if (d["capability_id"], d["capability_version"])
                         == (selected.capability_id, selected.capability_version)],
        "units": ({"temperature_c": "degrees_celsius"} if device == "temperature"
                  else {"position_percent": "percent"} if device == "curtain" else {}),
        "cases": results, "dispatch_count": sum(r["dispatch_count"] for r in results),
        "verified": True,
    }
