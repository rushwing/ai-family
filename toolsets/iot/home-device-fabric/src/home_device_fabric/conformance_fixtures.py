"""Explicit offline-profile stimuli and independent expected observations (REQ-021)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

Json = dict[str, Any]
HOME = "home-demo"
INSTANCE = "mock-demo"
TIME = "2026-01-01T00:00:00Z"
# These are contract expectations, not read from demo/model verdicts.
MEMBERS = {"switch": "is_on", "curtain": "position_percent", "temperature": "temperature_c"}
CAPABILITIES = {
    "switch": "home.switchable",
    "curtain": "home.positionable",
    "temperature": "home.temperature_sensor",
}
DEADLINES = {"switch": 30_000, "curtain": 120_000, "temperature": 0}


@dataclass(frozen=True)
class Case:
    case_id: str
    obligation: str
    kind: str
    device: str = "switch"
    target: object = True
    reports: tuple[tuple[int, object, int, int], ...] = ()
    expected_state: str | None = None
    expected_value: object = False
    offline: bool = False
    known: bool = True
    mutation: str = ""


CASES = (
    Case("discovery", "provider", "discovery"),
    Case("catalogue", "caller", "catalogue"),
    *(
        Case("provider-" + name, "provider", "reject", mutation=name)
        for name in ("binding", "arguments", "accepted", "support", "attempt", "action", "revision")
    ),
    Case(
        "switch-on",
        "integration",
        "flow",
        reports=((10, True, 1, 2),),
        expected_state="succeeded",
        expected_value=True,
    ),
    Case(
        "switch-off",
        "integration",
        "flow",
        target=False,
        reports=((10, False, 1, 2),),
        expected_state="succeeded",
    ),
    Case(
        "curtain-closed",
        "integration",
        "flow",
        "curtain",
        0,
        ((5, 60, 1, 2), (10, 0, 1, 3)),
        "succeeded",
        0,
    ),
    Case(
        "curtain-open",
        "integration",
        "flow",
        "curtain",
        100,
        ((5, 40, 1, 2), (10, 100, 1, 3)),
        "succeeded",
        100,
    ),
    Case(
        "curtain-partial",
        "integration",
        "flow",
        "curtain",
        40,
        ((5, 20, 1, 2), (10, 40, 1, 3)),
        "succeeded",
        40,
    ),
    *(
        Case(
            device + "-" + name,
            "mock-scheduling",
            "flow",
            device,
            True if device == "switch" else 40,
            reports,
            "timed_out",
            value,
            mutation=name,
        )
        for device in ("switch", "curtain")
        for name, reports, value in (
            ("timeout", (), False if device == "switch" else 0),
            (
                "mismatch",
                ((10, False if device == "switch" else 20, 1, 2),),
                False if device == "switch" else 20,
            ),
            (
                "stale",
                ((10, True if device == "switch" else 40, 1, 1),),
                False if device == "switch" else 0,
            ),
            (
                "wrong-epoch",
                ((10, True if device == "switch" else 40, 0, 2),),
                False if device == "switch" else 0,
            ),
            (
                "deadline-tie",
                ((DEADLINES[device], True if device == "switch" else 40, 1, 2),),
                True if device == "switch" else 40,
            ),
            (
                "late",
                ((DEADLINES[device] + 1, True if device == "switch" else 40, 1, 2),),
                True if device == "switch" else 40,
            ),
        )
    ),
    *(
        Case(
            device + "-failed",
            "integration",
            "flow",
            device,
            True if device == "switch" else 40,
            expected_state="failed",
            expected_value=False if device == "switch" else 0,
            mutation="failed",
        )
        for device in ("switch", "curtain")
    ),
    *(
        Case(
            device + "-offline-" + label,
            "caller",
            "flow",
            device,
            True if device == "switch" else 40,
            offline=True,
            known=known,
            expected_value=False if device == "switch" else 0,
        )
        for device in ("switch", "curtain", "temperature")
        for label, known in (("unknown", False), ("known", True))
    ),
    *(
        Case("switch-invalid-" + str(i), "caller", "flow", target=value, mutation="invalid")
        for i, value in enumerate((0, 1, "true", None))
    ),
    *(
        Case(
            "curtain-invalid-" + str(i),
            "caller",
            "flow",
            "curtain",
            value,
            expected_value=0,
            mutation="invalid",
        )
        for i, value in enumerate((-1, 101, 1.5, True))
    ),
    *(
        Case("request-" + name, "caller", "flow", mutation=name)
        for name in ("action", "member", "revision")
    ),
    Case("temperature-observe", "caller", "sensor", "temperature", expected_value=21.25),
    Case(
        "temperature-write",
        "caller",
        "flow",
        "temperature",
        22,
        expected_value=0,
        mutation="invalid",
    ),
    Case("replay", "caller", "replay"),
    Case("conflict", "caller", "replay", mutation="conflict"),
    Case("replay-invalid-type", "caller", "replay", mutation="invalid-type"),
    Case("provider-ordering", "provider", "ordering"),
)


def request(case: Case, *, suffix: str = "") -> Json:
    return {
        "schema_version": 1,
        "home_id": HOME,
        "device_id": "device-" + case.device,
        "capability_id": CAPABILITIES[case.device],
        "capability_version": 1,
        "action_id": {
            "switch": "set_on",
            "curtain": "set_position",
            "temperature": "write_temperature",
        }[case.device],
        "arguments": {MEMBERS[case.device]: case.target},
        "idempotency_key": "key-" + case.case_id,
        "trace_id": "trace-" + case.case_id + suffix,
    }


def input_record(
    case: Case,
    value: object,
    sequence: int,
    *,
    epoch: int = 1,
    availability: bool = False,
    correlated: bool = False,
) -> Json:
    payload: Json = {"observed_at": TIME, "ordering": {"epoch": epoch, "sequence": sequence}}
    payload.update({"status": value} if availability else {"status": "known", "value": value})
    return {
        "schema_version": 1,
        "provider": "mock",
        "provider_instance_id": INSTANCE,
        "home_id": HOME,
        "device_id": "device-" + case.device,
        "kind": "availability" if availability else "property",
        "capability_id": None if availability else CAPABILITIES[case.device],
        "capability_version": None if availability else 1,
        "member": None if availability else MEMBERS[case.device],
        "payload": payload,
        "correlation": {"task_id": "task-" + case.case_id, "trace_id": "trace-" + case.case_id}
        if correlated
        else None,
    }


def result(task: Json, state: str, evidence: Json | None = None) -> Json:
    return {
        "schema_version": 1,
        "task_id": task["task_id"],
        "trace_id": task["trace_id"],
        **{
            k: task["request"][k]
            for k in ("home_id", "device_id", "capability_id", "capability_version", "action_id")
        },
        "state": state,
        "output": {"present": False, "value": None},
        "error": {"code": "scripted_failure"} if state == "failed" else None,
        "evidence": evidence,
        "physical_outcome": "confirmed" if state == "succeeded" else "unverified",
    }


def evidence(task: Json, kind: str) -> Json:
    return {
        "kind": kind,
        "task_id": task["task_id"],
        "trace_id": task["trace_id"],
        **{
            k: task["request"][k]
            for k in ("home_id", "device_id", "capability_id", "capability_version", "action_id")
        },
    }


def outcome(task: Json, state: str = "running") -> Json:
    return {
        "schema_version": 1,
        "provider": "mock",
        "provider_instance_id": INSTANCE,
        "result": result(task, state, evidence(task, "ack") if state == "running" else None),
    }
