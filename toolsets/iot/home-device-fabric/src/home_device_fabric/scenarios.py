"""Authoritative fictional demo stimuli; reports never derive from submitted intent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from state_schema.initial_capabilities import load_initial_capabilities
from state_schema.provider_contracts import DeviceRegistration, MockConfiguration

Json = dict[str, Any]
HOME = "home-demo"
INSTANCE = "mock-demo"
TIME = "2026-01-01T00:00:00Z"


class _Model:
    device: ClassVar[str]
    capability_version: ClassVar[int] = 1
    device_id: str

    def build(self, scenario: str) -> tuple[DemoCase, ...]:
        return build_scenario(self.device, scenario)

    def registration(self) -> DeviceRegistration:
        return MockConfiguration.from_dict(configuration()).registration(HOME, self.device_id)


@dataclass(frozen=True)
class MockSwitch(_Model):
    device: ClassVar[str] = "switch"
    device_id: str = "device-switch"
    capability_id: str = "home.switchable"
    member: str = "is_on"
    action_id: str = "set_on"
    timeout_ms: int = 30_000


@dataclass(frozen=True)
class MockCurtain(_Model):
    device: ClassVar[str] = "curtain"
    device_id: str = "device-curtain"
    capability_id: str = "home.positionable"
    member: str = "position_percent"
    action_id: str = "set_position"
    timeout_ms: int = 120_000


@dataclass(frozen=True)
class MockTemperatureSensor(_Model):
    device: ClassVar[str] = "temperature"
    device_id: str = "device-temperature"
    capability_id: str = "home.temperature_sensor"
    member: str = "temperature_c"
    # Deliberately nonexistent action for write-rejected; the sensor has no actions.
    action_id: str = "write_temperature"
    timeout_ms: int = 0


Model = MockSwitch | MockCurtain | MockTemperatureSensor
MODELS: dict[str, Model] = {
    "switch": MockSwitch(), "curtain": MockCurtain(), "temperature": MockTemperatureSensor(),
}


class DemoError(ValueError):
    """Only fixed value-free codes cross the CLI boundary."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class DemoCase:
    name: str
    device: str
    initial_inputs: tuple[Json, ...]
    request: Json | None
    deliveries: tuple[Json, ...]
    observations: tuple[tuple[int, Json], ...]
    expected_task: str | None
    expected_rejection: str | None
    horizon_ms: int

    @property
    def task_id(self) -> str:
        return "task-" + self.name

    @property
    def trace_id(self) -> str:
        return "trace-" + self.name


def configuration() -> Json:
    """Fresh validated configuration discovers all three separate canonical devices."""
    models = tuple(MODELS.values())
    data = {
        "schema_version": 1, "provider": "mock", "provider_instance_id": INSTANCE,
        "inventory": {
            "schema_version": 1,
            "home": {"id": HOME, "name": "Fictional demo", "residence_type": "apartment"},
            "floors": [], "areas": [], "labels": [], "area_groups": [],
            "devices": [
                {"id": m.device_id, "home_id": HOME, "name": m.device_id,
                 "area_id": None, "labels": []} for m in models
            ],
        },
        "bindings": {"schema_version": 1, "bindings": [
            {"home_id": HOME, "device_id": m.device_id, "provider": "mock",
             "provider_instance_id": INSTANCE, "mapping": {"device_key": m.device_id}}
            for m in models
        ]},
        "catalogue": load_initial_capabilities().to_dict(),
        "devices": [
            {"home_id": HOME, "device_id": m.device_id, "supported_capabilities": [
                {"capability_id": m.capability_id, "capability_version": 1}
            ]} for m in models
        ],
        "scenarios": [],
    }
    return MockConfiguration.from_dict(data).to_dict()


def _input(model: Model, value: object, sequence: int, *, availability: bool = False,
           epoch: int = 1, name: str | None = None) -> Json:
    payload: Json = {"observed_at": TIME, "ordering": {"epoch": epoch, "sequence": sequence}}
    if availability:
        payload.update(status=value)
    else:
        payload.update(status="known", value=value)
    return {
        "schema_version": 1, "provider": "mock", "provider_instance_id": INSTANCE,
        "home_id": HOME, "device_id": model.device_id,
        "kind": "availability" if availability else "property",
        "capability_id": None if availability else model.capability_id,
        "capability_version": None if availability else 1,
        "member": None if availability else model.member, "payload": payload,
        "correlation": None if name is None else {
            "task_id": "task-" + name, "trace_id": "trace-" + name,
        },
    }


def _case(device: str, name: str, target: object, reports: tuple[tuple[int, object], ...],
          *, expected: str = "succeeded", offline: bool = False, known: bool = True,
          rejection: str | None = None, epoch: int = 1, sequence: int = 2) -> DemoCase:
    model = MODELS[device]
    initial: list[Json] = [_input(model, "offline" if offline else "online", 1,
                                 availability=True)]
    if known:
        initial.append(_input(model, False if device == "switch" else 0, 1))
    request = {
        "schema_version": 1, "home_id": HOME, "device_id": model.device_id,
        "capability_id": model.capability_id, "capability_version": 1,
        "action_id": model.action_id, "arguments": {model.member: target},
        "idempotency_key": "key-" + name, "trace_id": "trace-" + name,
    }
    deliveries = tuple(
        {"delay_ms": delay, "input": _input(model, value, sequence + i,
                                              epoch=epoch, name=name), "outcome": None}
        for i, (delay, value) in enumerate(reports)
    )
    return DemoCase(name, device, tuple(initial), request, deliveries, (),
                    None if rejection else expected, rejection, model.timeout_ms + 100)


def build_scenario(device: str, scenario: str) -> tuple[DemoCase, ...]:
    """Each fresh fixture contains literal requests and separately declared reports."""
    if device not in MODELS:
        raise DemoError("unsupported_scenario")
    model = MODELS[device]
    prefix = device + "-"
    if scenario == "offline":
        if device == "temperature":
            return tuple(DemoCase(
                prefix + "offline-" + label, device,
                tuple([_input(model, "offline", 1, availability=True)] +
                      ([_input(model, 0, 1)] if known else [])),
                None, (), (), None, None, 0,
            ) for label, known in (("unknown", False), ("known", True)))
        return tuple(_case(device, prefix + "offline-" + label, True if device == "switch" else 40,
                           (), offline=True, known=known, rejection="offline")
                     for label, known in (("unknown", False), ("known", True)))
    if device == "temperature":
        if scenario == "observe":
            return (DemoCase(prefix + "observe", device,
                             (_input(model, "online", 1, availability=True),), None, (),
                             tuple((i * 10, _input(model, value, i + 1))
                                   for i, value in enumerate((0, -5.5, 21.25))),
                             None, None, 20),)
        if scenario == "write-rejected":
            return (_case(device, prefix + "write", 22, (), rejection="invalid_request"),)
        raise DemoError("unsupported_scenario")
    if scenario == "success":
        if device == "switch":
            return (_case(device, prefix + "on", True, ((10, True),)),
                    _case(device, prefix + "off", False, ((10, False),)))
        return (_case(device, prefix + "closed", 0, ((5, 60), (10, 0))),
                _case(device, prefix + "open", 100, ((5, 40), (10, 100))),
                _case(device, prefix + "partial", 40, ((5, 20), (10, 40))))
    if device == "curtain" and scenario == "invalid-position":
        return tuple(_case(device, prefix + "invalid-" + str(i), value, (),
                           rejection="invalid_request")
                     for i, value in enumerate((-1, 101, 1.5, True)))
    if device == "switch" and scenario == "malformed":
        return tuple(_case(device, prefix + "malformed-" + str(i), value, (),
                           rejection="invalid_request")
                     for i, value in enumerate((0, 1, "true", None)))
    # Literal future reports remain independent even if a caller edits a request.
    target = True if device == "switch" else 40
    if scenario == "timeout":
        return (_case(device, prefix + scenario, target, (), expected="timed_out"),)
    if scenario == "mismatch":
        return (_case(device, prefix + scenario, target,
                      ((10, False if device == "switch" else 20),), expected="timed_out"),)
    if scenario in ("stale", "wrong-epoch"):
        return (_case(device, prefix + scenario, target,
                      ((10, True if device == "switch" else 40),), expected="timed_out",
                      epoch=0 if scenario == "wrong-epoch" else 1,
                      sequence=1 if scenario == "stale" else 2),)
    if scenario in ("deadline-tie", "late"):
        return (_case(device, prefix + scenario, target,
                      ((model.timeout_ms + (1 if scenario == "late" else 0),
                        True if device == "switch" else 40),), expected="timed_out"),)
    raise DemoError("unsupported_scenario")
