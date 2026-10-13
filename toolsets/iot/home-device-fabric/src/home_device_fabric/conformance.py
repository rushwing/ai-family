"""Reusable, independently asserted offline provider profile and JSON CLI (REQ-021)."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Callable
from typing import NoReturn, cast

from state_schema import action_contracts as actions
from state_schema.canonical_state import StateError, apply_state_update
from state_schema.provider_contracts import MockConfiguration, NormalizedInput, ProviderError

from .conformance_catalogue import CATALOGUE_JSON
from .conformance_fixtures import (
    CAPABILITIES,
    CASES,
    DEADLINES,
    HOME,
    MEMBERS,
    Case,
    Json,
    evidence,
    input_record,
    outcome,
    request,
    result,
)
from .mock import MockProvider, ProviderProtocol
from .scenarios import configuration

PROFILE = "offline-provider-v1"
INVENTORY_VERSION = 1
INVENTORY_SHA256 = "0cb57579e3eb82bb1d7c73722f1c5e3c386427d45c7efde9ed011a5c7f18e6bd"
_MANIFEST = tuple((c.case_id, c.obligation) for c in CASES)
_REQUESTER = {
    "subject_id": "subject-conformance",
    "family_member_id": "member-conformance",
    "home_id": HOME,
    "role": "adult",
}


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _copy(value: object) -> Json:
    return cast(Json, json.loads(canonical_json(value)))


def _same(left: object, right: object) -> bool:
    return canonical_json(left) == canonical_json(right)


def expected_inventory() -> list[Json]:
    return [{"case_id": identity, "obligation": obligation} for identity, obligation in _MANIFEST]


class _CheckFailed(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise _CheckFailed(code)


class ConformanceDriver:
    """Offline stimulus factory result; caller policy is distinct from the provider."""

    def __init__(self, provider: ProviderProtocol) -> None:
        self.provider = provider

    def dispatch(self, task: object, *, binding: object, attempt_id: object, verdict: str) -> None:
        if verdict == "dispatch":
            self.provider.submit(task, binding=binding, attempt_id=attempt_id)
        elif verdict not in ("replay", "conflict", "offline", "invalid"):
            raise _CheckFailed("policy_mismatch")


def mock_factory(configuration_data: object) -> ConformanceDriver:
    return ConformanceDriver(MockProvider(configuration_data))


Factory = Callable[[object], ConformanceDriver]


def _driver(factory: Factory, data: Json) -> ConformanceDriver:
    try:
        driver = factory(MockConfiguration.from_dict(data).to_dict())
    except Exception:
        raise _CheckFailed("setup_failed") from None
    if not isinstance(driver, ConformanceDriver) or not isinstance(
        driver.provider, ProviderProtocol
    ):
        raise _CheckFailed("setup_failed")
    return driver


def _task(case: Case, data: Json, *, suffix: str = "", incoming: Json | None = None) -> Json:
    accepted = actions.create_task(
        request(case, suffix=suffix) if incoming is None else incoming,
        requester=_REQUESTER,
        task_id="task-" + case.case_id + suffix,
        inventory=data["inventory"],
        catalogue=data["catalogue"],
    )
    return actions.transition_task(
        accepted,
        result(accepted, "running"),
        inventory=data["inventory"],
        catalogue=data["catalogue"],
        dispatch_context={"current_epoch": 1, "baseline": {"epoch": 1, "sequence": 1}},
    )


def _script(data: Json, task: Json, deliveries: list[Json]) -> None:
    data["scenarios"].append(
        {"task_id": task["task_id"], "attempt_id": "attempt-conformance", "deliveries": deliveries}
    )


def _binding(provider: ProviderProtocol, device: str) -> Json:
    return next(
        r.binding.to_dict() for r in provider.discover() if r.device_id == "device-" + device
    )


def _discovery(factory: Factory, data: Json, actual: Json) -> None:
    p = _driver(factory, data).provider
    first = [r.to_dict() for r in p.discover()]
    actual["discovery"] = first
    expected = cast(Json, MockConfiguration.from_dict(data).to_dict())
    for reg, device in zip(first, ("switch", "curtain", "temperature"), strict=True):
        _require(
            reg["home_id"] == HOME and reg["device_id"] == "device-" + device, "identity_mismatch"
        )
        _require(
            _same(
                reg["supported_capabilities"],
                [{"capability_id": CAPABILITIES[device], "capability_version": 1}],
            ),
            "identity_mismatch",
        )
        binding = expected["bindings"]["bindings"][
            ("switch", "curtain", "temperature").index(device)
        ]
        _require(_same(reg["binding"], binding), "identity_mismatch")
    _require(_same(first, [r.to_dict() for r in p.discover()]), "identity_mismatch")
    fresh = _driver(factory, data).provider
    _require(
        fresh is not p and _same(first, [r.to_dict() for r in fresh.discover()]),
        "identity_mismatch",
    )
    mutable = cast(Json, p.discover()[0].to_dict())
    mutable["binding"]["mapping"]["device_key"] = "changed"
    _require(_same(first, [r.to_dict() for r in p.discover()]), "identity_mismatch")
    states = [s.to_dict() for s in p.snapshot()]
    actual["snapshots"] = states
    _require(
        [s["device_id"] for s in states]
        == ["device-switch", "device-curtain", "device-temperature"],
        "state_mismatch",
    )
    for s in states:
        _require(
            s["home_id"] == HOME
            and s["desired_state"] is None
            and s["reported_state"] == {}
            and s["availability"] == {"status": "unknown", "observed_at": None, "ordering": None},
            "state_mismatch",
        )
    mutable_state = cast(Json, p.snapshot()[0].to_dict())
    mutable_state["availability"]["status"] = "offline"
    _require(_same(states, [s.to_dict() for s in p.snapshot()]), "state_mismatch")


def _catalogue(data: Json, actual: Json) -> None:
    selected = [
        d
        for d in data["catalogue"]["capabilities"]
        if (d["capability_id"], d["capability_version"])
        in {(name, 1) for name in CAPABILITIES.values()}
    ]
    actual["descriptors"] = selected
    actual["units"] = {"temperature_c": "degrees_celsius", "position_percent": "percent"}
    _require(_same(selected, json.loads(CATALOGUE_JSON)), "catalogue_mismatch")


def _reject(case: Case, factory: Factory, data: Json, actual: Json) -> None:
    task = _task(case, data)
    _script(data, task, [])
    if case.mutation == "support":
        data["devices"][0]["supported_capabilities"] = []
    p = _driver(factory, data).provider
    binding = _binding(p, case.device)
    attempt = "attempt-conformance"
    expected = "invalid_task"
    if case.mutation == "binding":
        binding["mapping"]["device_key"] = "wrong"
        expected = "binding_mismatch"
    elif case.mutation == "arguments":
        task["request"]["arguments"]["is_on"] = 1
    elif case.mutation == "accepted":
        task = actions.create_task(
            request(case),
            requester=_REQUESTER,
            task_id=task["task_id"],
            inventory=data["inventory"],
            catalogue=data["catalogue"],
        )
    elif case.mutation == "support":
        expected = "unsupported"
    elif case.mutation == "attempt":
        attempt = "missing"
        expected = "invalid_attempt"
    elif case.mutation == "action":
        task["request"]["action_id"] = "missing_action"
    elif case.mutation == "revision":
        task["request"]["capability_version"] = 2
    code = None
    try:
        p.submit(task, binding=binding, attempt_id=attempt)
    except ProviderError as exc:
        code = exc.code
    actual.update(rejection=code, dispatches=list(p.dispatch_log), deliveries=list(p.delivery_log))
    _require(code == expected, "rejection_mismatch")
    _require(
        p.dispatch_log == () and p.delivery_log == () and list(p.advance(200_000)) == [],
        "invalid_dispatch",
    )


def _flow(case: Case, factory: Factory, data: Json, actual: Json) -> None:
    task: Json | None = None
    incoming = request(case)
    if case.mutation == "action":
        incoming["action_id"] = "missing_action"
    elif case.mutation == "member":
        incoming["arguments"] = {"missing_member": True}
    elif case.mutation == "revision":
        incoming["capability_version"] = 2
    rejection = None
    if case.kind != "sensor" and not (case.device == "temperature" and case.offline):
        try:
            task = _task(case, data, incoming=incoming)
        except actions.ActionError:
            rejection = "invalid_request"
    if task is not None:
        deliveries = [{"delay_ms": 0, "input": None, "outcome": outcome(task)}]
        deliveries.extend(
            {
                "delay_ms": time,
                "input": input_record(case, value, sequence, epoch=epoch, correlated=True),
                "outcome": None,
            }
            for time, value, epoch, sequence in case.reports
        )
        if case.mutation == "failed":
            deliveries.append({"delay_ms": 10, "input": None, "outcome": outcome(task, "failed")})
        # Settlement must suppress this later ACK on all action paths.
        deliveries.append(
            {"delay_ms": DEADLINES[case.device] + 50, "input": None, "outcome": outcome(task)}
        )
        _script(data, task, deliveries)
    expected_deliveries: list[Json] = []
    if task is not None and not case.offline:
        expected_deliveries = [
            {"time_ms": d["delay_ms"], "input": d["input"], "outcome": d["outcome"]}
            for d in data["scenarios"][0]["deliveries"]
            if d["delay_ms"] <= DEADLINES[case.device]
        ]
        # Inputs after timeout remain deliverable; later action outcomes are suppressed.
        expected_deliveries.extend(
            {"time_ms": d["delay_ms"], "input": d["input"], "outcome": None}
            for d in data["scenarios"][0]["deliveries"]
            if d["delay_ms"] > DEADLINES[case.device] and d["input"] is not None
        )
        if case.expected_state == "timed_out":
            timed_out = result(task, "timed_out")
            timed_out["error"] = {"code": "provider_timeout"}
            expected_deliveries.append(
                {
                    "time_ms": DEADLINES[case.device],
                    "input": None,
                    "outcome": {
                        "schema_version": 1,
                        "provider": "mock",
                        "provider_instance_id": "mock-demo",
                        "result": timed_out,
                    },
                }
            )
        expected_deliveries.sort(
            key=lambda d: (
                d["time_ms"],
                0 if d["outcome"] and d["outcome"]["result"]["state"] == "timed_out" else 1,
            )
        )
    driver = _driver(factory, data)
    p = driver.provider
    state = next(
        cast(Json, s.to_dict()) for s in p.snapshot() if s.device_id == "device-" + case.device
    )
    actual["initial_state"] = _copy(state)
    _require(
        state["reported_state"] == {} and state["availability"]["status"] == "unknown",
        "state_mismatch",
    )
    timeline: list[Json] = []
    actual["timeline"] = timeline

    def observe(raw: Json, time: int) -> None:
        nonlocal state, task
        inp = NormalizedInput.from_dict(
            raw, configuration=MockConfiguration.from_dict(data)
        ).to_dict()
        applied = True
        try:
            state = apply_state_update(
                state,
                current_epoch=1,
                reported_state={inp["member"]: inp["payload"]}
                if inp["kind"] == "property"
                else None,
                availability=inp["payload"] if inp["kind"] == "availability" else None,
            )
        except StateError:
            applied = False
        if applied and inp["correlation"] and task is not None and task["state"] == "running":
            try:
                completed = actions.transition_task(
                    task,
                    result(task, "succeeded", {**evidence(task, "state"), "state": state}),
                    inventory=data["inventory"],
                    catalogue=data["catalogue"],
                )
            except actions.ActionError:
                pass
            else:
                task = completed
                p.settle(task)
        timeline.append(
            {
                "time_ms": time,
                "kind": "input",
                "record": inp,
                "applied": applied,
                "task_state": None if task is None else task["state"],
                "state": _copy(state),
            }
        )

    observe(input_record(case, "offline" if case.offline else "online", 1, availability=True), 0)
    if case.known and case.kind != "sensor":
        observe(input_record(case, False if case.device == "switch" else 0, 1), 0)
    actual["ready_state"] = _copy(state)
    if case.offline and task is not None:
        driver.dispatch(
            task,
            binding=_binding(p, case.device),
            attempt_id="attempt-conformance",
            verdict="offline",
        )
        task = None
        rejection = "offline"
    elif rejection is not None:
        driver.dispatch(
            None,
            binding=_binding(p, case.device),
            attempt_id="attempt-conformance",
            verdict="invalid",
        )
    elif task is not None:
        driver.dispatch(
            task,
            binding=_binding(p, case.device),
            attempt_id="attempt-conformance",
            verdict="dispatch",
        )
        horizon = DEADLINES[case.device] + 100
        yielded: list[Json] = []
        actual["yielded"] = yielded
        for delivery in p.advance(horizon):
            yielded.append(cast(Json, delivery.to_dict()))
            if delivery.input is not None:
                observe(delivery.input.to_dict(), delivery.time_ms)
            elif delivery.outcome is not None:
                raw = cast(Json, delivery.outcome.to_dict())
                r = raw["result"]
                _require(task is not None and task["state"] == "running", "completion_mismatch")
                _require(r["state"] in ("running", "failed", "timed_out"), "completion_mismatch")
                if r["state"] == "running":
                    actions.validate_result(
                        r, task=task, inventory=data["inventory"], catalogue=data["catalogue"]
                    )
                else:
                    task = actions.transition_task(
                        task, r, inventory=data["inventory"], catalogue=data["catalogue"]
                    )
                    p.settle(task)
                timeline.append(
                    {
                        "time_ms": delivery.time_ms,
                        "kind": "outcome",
                        "record": raw,
                        "task_state": task["state"],
                    }
                )
        _require(_same(yielded, expected_deliveries), "delivery_mismatch")
        _require(_same(list(p.delivery_log), yielded), "delivery_mismatch")
        repeated = [d.to_dict() for d in p.advance(horizon)]
        actual["repeated"] = repeated
        _require(repeated == [] and p.now_ms == horizon, "delivery_mismatch")
    if case.kind == "sensor":
        for time, value, seq in ((0, 0, 1), (10, -5.5, 2), (20, 21.25, 3)):
            observe(input_record(case, value, seq), time)
    actual.update(
        final_state=state,
        task=task,
        rejection=rejection,
        dispatches=list(p.dispatch_log),
        deliveries=list(p.delivery_log),
    )
    _require(
        (None if task is None else task["state"]) == case.expected_state, "completion_mismatch"
    )
    invalid = case.mutation in ("invalid", "action", "member", "revision")
    expected_rejection = (
        "invalid_request"
        if invalid
        else ("offline" if case.offline and case.device != "temperature" else None)
    )
    _require(rejection == expected_rejection, "rejection_mismatch")
    _require(len(p.dispatch_log) == (1 if case.expected_state else 0), "invalid_dispatch")
    _require(
        state["availability"]["status"] == ("offline" if case.offline else "online"),
        "state_mismatch",
    )
    reported = state["reported_state"]
    _require(
        _same(reported.get(MEMBERS[case.device], {}).get("value"), case.expected_value)
        if case.known
        else reported == {},
        "state_mismatch",
    )
    if task is not None:
        _require(
            task["result"]["physical_outcome"]
            == ("confirmed" if case.expected_state == "succeeded" else "unverified"),
            "completion_mismatch",
        )
        outcomes = [item for item in timeline if item["kind"] == "outcome"]
        _require(
            outcomes[0]["time_ms"] == 0 and outcomes[0]["task_state"] == "running",
            "completion_mismatch",
        )
        if case.expected_state == "timed_out":
            _require(
                outcomes[-1]["time_ms"] == DEADLINES[case.device]
                and outcomes[-1]["record"]["result"]["error"] == {"code": "provider_timeout"},
                "delivery_mismatch",
            )
        if case.expected_state == "succeeded":
            _require(
                all(x["task_state"] == "running" for x in timeline if x["time_ms"] == 5),
                "completion_mismatch",
            )
        if case.mutation in ("stale", "wrong-epoch"):
            _require(
                not next(x for x in timeline if x["time_ms"] == 10)["applied"], "state_mismatch"
            )


def _replay(case: Case, factory: Factory, data: Json, actual: Json) -> None:
    task = _task(case, data)
    incoming = request(case, suffix="-candidate")
    if case.mutation == "conflict":
        incoming["arguments"]["is_on"] = False
    elif case.mutation == "invalid-type":
        incoming["arguments"]["is_on"] = 1
    _script(data, task, [])
    candidate: Json | None = None
    try:
        verdict = actions.compare_idempotency(
            task,
            incoming,
            requester=_REQUESTER,
            inventory=data["inventory"],
            catalogue=data["catalogue"],
        )
        candidate = _task(case, data, suffix="-candidate", incoming=incoming)
        _script(data, candidate, [])
    except actions.ActionError:
        verdict = "invalid"
    driver = _driver(factory, data)
    binding = _binding(driver.provider, case.device)
    driver.dispatch(task, binding=binding, attempt_id="attempt-conformance", verdict="dispatch")
    driver.dispatch(candidate, binding=binding, attempt_id="attempt-conformance", verdict=verdict)
    actual.update(
        verdict=verdict,
        original_task=task,
        candidate=candidate,
        dispatches=list(driver.provider.dispatch_log),
    )
    expected = {"": "replay", "conflict": "conflict", "invalid-type": "invalid"}[case.mutation]
    _require(verdict == expected, "policy_mismatch")
    _require(len(driver.provider.dispatch_log) == 1, "invalid_dispatch")


def _ordering(case: Case, factory: Factory, data: Json, actual: Json) -> None:
    task = _task(case, data)
    records = [
        input_record(case, False, 2),
        input_record(case, True, 1),
        input_record(case, True, 3, epoch=0),
    ]
    _script(
        data,
        task,
        [{"delay_ms": i * 10, "input": raw, "outcome": None} for i, raw in enumerate(records)],
    )
    p = _driver(factory, data).provider
    p.submit(task, binding=_binding(p, case.device), attempt_id="attempt-conformance")
    deliveries = [d.to_dict() for d in p.advance(20)]
    state = next(cast(Json, s.to_dict()) for s in p.snapshot() if s.device_id == "device-switch")
    actual.update(deliveries=deliveries, snapshot=state)
    _require(
        len(deliveries) == 3
        and state["reported_state"]["is_on"]
        == {
            "status": "known",
            "value": False,
            "observed_at": "2026-01-01T00:00:00Z",
            "ordering": {"epoch": 1, "sequence": 2},
        },
        "state_mismatch",
    )


def run_conformance(factory: Factory = mock_factory) -> Json:
    cases: list[Json] = []
    for case in CASES:
        actual: Json = {}
        error = None
        try:
            data = configuration()
            if case.kind == "discovery":
                _discovery(factory, data, actual)
            elif case.kind == "catalogue":
                _catalogue(data, actual)
            elif case.kind == "reject":
                _reject(case, factory, data, actual)
            elif case.kind == "replay":
                _replay(case, factory, data, actual)
            elif case.kind == "ordering":
                _ordering(case, factory, data, actual)
            else:
                _flow(case, factory, data, actual)
        except _CheckFailed as exc:
            error = exc.code
        except Exception:
            # Library callers inspect fixed diagnostics/evidence; never raw user exceptions.
            error = "check_failed"
        try:
            if not _strict_json(actual):
                raise ValueError("invalid evidence")
            actual = _copy(actual)
        except Exception:
            actual = {"diagnostic": "invalid_evidence"}
            error = "check_failed"
        cases.append(
            {
                "case_id": case.case_id,
                "obligation": case.obligation,
                "executed": True,
                "status": "passed" if error is None else "failed",
                "evidence": actual,
                "error": error,
            }
        )
    passed = sum(c["status"] == "passed" for c in cases)
    report = {
        "schema_version": 1,
        "simulation": True,
        "profile": PROFILE,
        "inventory_version": INVENTORY_VERSION,
        "inventory_sha256": INVENTORY_SHA256,
        "expected_cases": expected_inventory(),
        "cases": cases,
        "counts": {
            "total": len(cases),
            "executed": len(cases),
            "passed": passed,
            "failed": len(cases) - passed,
            "skipped": 0,
        },
        "passed": False,
    }
    report["passed"] = passed == len(_MANIFEST) and len(cases) == len(_MANIFEST)
    if not validate_report(report):
        report["passed"] = False
    return report


def validate_report(report: object) -> bool:
    """Verify the complete trusted inventory and exact report shape, never its verdict alone."""
    try:
        if type(report) is not dict:
            return False
        r = cast(Json, report)
        if set(r) != {
            "schema_version",
            "simulation",
            "profile",
            "inventory_version",
            "inventory_sha256",
            "expected_cases",
            "cases",
            "counts",
            "passed",
        }:
            return False
        expected = expected_inventory()
        if hashlib.sha256(canonical_json(expected).encode()).hexdigest() != INVENTORY_SHA256:
            return False
        if (
            type(r["schema_version"]) is not int
            or r["schema_version"] != 1
            or r["simulation"] is not True
            or r["profile"] != PROFILE
            or type(r["inventory_version"]) is not int
            or r["inventory_version"] != 1
            or r["inventory_sha256"] != INVENTORY_SHA256
            or not _same(r["expected_cases"], expected)
            or r["passed"] is not True
        ):
            return False
        if type(r["cases"]) is not list or len(r["cases"]) != len(expected):
            return False
        for case, item in zip(r["cases"], expected, strict=True):
            if (
                type(case) is not dict
                or set(case) != {"case_id", "obligation", "executed", "status", "evidence", "error"}
                or case["case_id"] != item["case_id"]
                or case["obligation"] != item["obligation"]
                or case["executed"] is not True
                or case["status"] != "passed"
                or case["error"] is not None
                or type(case["evidence"]) is not dict
                or not case["evidence"]
            ):
                return False
        if not _same(
            r["counts"],
            {
                "total": len(expected),
                "executed": len(expected),
                "passed": len(expected),
                "failed": 0,
                "skipped": 0,
            },
        ):
            return False
        # Round-trip prevents tuples and non-string keys from masquerading as strict JSON.
        return _strict_json(r)
    except (ValueError, TypeError, KeyError, RecursionError, OverflowError):
        return False


def _strict_json(value: object) -> bool:
    if value is None or type(value) in (str, bool, int):
        return True
    if type(value) is float:
        canonical_json(value)  # rejects NaN/Infinity
        return True
    if type(value) is list:
        return all(_strict_json(v) for v in cast(list[object], value))
    if type(value) is dict:
        return all(type(k) is str and _strict_json(v) for k, v in cast(Json, value).items())
    return False


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.exit(2, "invalid_arguments\n")


def main() -> int:
    _Parser(description="Verify the fictional offline provider profile").parse_args()
    report = run_conformance()
    print(canonical_json(report))
    return 0 if validate_report(report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
