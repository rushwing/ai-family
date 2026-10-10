"""Fictional fixtures shared by tests and installed-artifact smoke."""

from state_schema.action_contracts import create_task, transition_task
from state_schema.initial_capabilities import load_initial_capabilities

HOME = "home-example"
DEVICE = "device-example"
INSTANCE = "mock-example"
TIME = "2026-01-01T00:00:00Z"


def inventory():
    return {
        "schema_version": 1,
        "home": {"id": HOME, "name": "Example", "residence_type": "apartment"},
        "floors": [],
        "areas": [],
        "devices": [
            {"id": DEVICE, "home_id": HOME, "name": "Example switch", "area_id": None, "labels": []}
        ],
        "labels": [],
        "area_groups": [],
    }


def binding():
    return {
        "home_id": HOME,
        "device_id": DEVICE,
        "provider": "mock",
        "provider_instance_id": INSTANCE,
        "mapping": {"device_key": "fictional-key"},
    }


def config():
    return {
        "schema_version": 1,
        "provider": "mock",
        "provider_instance_id": INSTANCE,
        "inventory": inventory(),
        "bindings": {"schema_version": 1, "bindings": [binding()]},
        "catalogue": load_initial_capabilities().to_dict(),
        "devices": [
            {
                "home_id": HOME,
                "device_id": DEVICE,
                "supported_capabilities": [
                    {"capability_id": "home.switchable", "capability_version": 1}
                ],
            }
        ],
        "scenarios": [],
    }


def request():
    return {
        "schema_version": 1,
        "home_id": HOME,
        "device_id": DEVICE,
        "capability_id": "home.switchable",
        "capability_version": 1,
        "action_id": "set_on",
        "arguments": {"is_on": False},
        "idempotency_key": "key-1",
        "trace_id": "trace-1",
    }


def requester():
    return {
        "subject_id": "subject-example",
        "family_member_id": "member-example",
        "home_id": HOME,
        "role": "adult",
    }


def result(task, state="running", evidence=None):
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
        "error": {"code": "provider_failed"} if state in ("failed", "timed_out") else None,
        "evidence": evidence,
        "physical_outcome": "confirmed" if state == "succeeded" else "unverified",
    }


def correlation(task):
    return {"task_id": task["task_id"], "trace_id": task["trace_id"]}


def evidence(task, kind="ack"):
    return {
        "kind": kind,
        **correlation(task),
        **{
            k: task["request"][k]
            for k in ("home_id", "device_id", "capability_id", "capability_version", "action_id")
        },
    }


def task(c=None, baseline=True, task_id="task-1", r=None):
    c = config() if c is None else c
    t = create_task(
        request() if r is None else r,
        requester=requester(),
        task_id=task_id,
        inventory=c["inventory"],
        catalogue=c["catalogue"],
    )
    return transition_task(
        t,
        result(t),
        inventory=c["inventory"],
        catalogue=c["catalogue"],
        dispatch_context={
            "current_epoch": 1,
            "baseline": {"epoch": 1, "sequence": 1} if baseline else None,
        },
    )


def input_record(kind="property", sequence=2, value=False, correlated=None, epoch=1):
    payload = {
        "status": "known",
        "value": value,
        "observed_at": TIME,
        "ordering": {"epoch": epoch, "sequence": sequence},
    }
    if kind == "availability":
        payload = {
            "status": "online",
            "observed_at": TIME,
            "ordering": {"epoch": epoch, "sequence": sequence},
        }
    return {
        "schema_version": 1,
        "provider": "mock",
        "provider_instance_id": INSTANCE,
        "home_id": HOME,
        "device_id": DEVICE,
        "kind": kind,
        "capability_id": None if kind == "availability" else "home.switchable",
        "capability_version": None if kind == "availability" else 1,
        "member": None if kind == "availability" else "is_on",
        "payload": payload,
        "correlation": correlated,
    }


def outcome(t, state="running"):
    return {
        "schema_version": 1,
        "provider": "mock",
        "provider_instance_id": INSTANCE,
        "result": result(t, state, evidence(t) if state in ("running", "acknowledged") else None),
    }


def script(c, t, deliveries=(), attempt="attempt-1"):
    c["scenarios"].append(
        {"task_id": t["task_id"], "attempt_id": attempt, "deliveries": list(deliveries)}
    )
    return c


def delivery(delay, item, is_outcome=False):
    return {
        "delay_ms": delay,
        "input": None if is_outcome else item,
        "outcome": item if is_outcome else None,
    }
