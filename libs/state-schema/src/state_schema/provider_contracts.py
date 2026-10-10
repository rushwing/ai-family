"""Strict, detached REQ-019 provider records; no provider execution or policy."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import cast

from .action_contracts import ActionError, ActionResult
from .canonical_state import Availability, Observation, Ordering, StateError
from .capability import CapabilityCatalogue, CapabilityError
from .home_inventory import CANONICAL_ID_PATTERN, Inventory, InventoryError
from .provider_binding import BindingCollection, BindingError, ProviderBinding

ErrorPath = tuple[str | int, ...]
_TOKEN = re.compile(r"[A-Za-z0-9._:-]{1,128}", re.ASCII)
_REASONS = {
    "invalid_json": "expected finite acyclic strict JSON within depth bounds",
    "invalid_configuration": "invalid provider configuration",
    "invalid_input": "invalid normalized provider input",
    "invalid_outcome": "invalid correlated provider outcome",
    "invalid_task": "eligible running task required",
    "binding_mismatch": "selected binding does not match configured binding",
    "unsupported": "device capability or interaction is unsupported",
    "invalid_attempt": "explicit unused scripted attempt required",
    "invalid_time": "nondecreasing nonnegative integer virtual time required",
    "invalid_settlement": "terminal settlement must match the frozen submitted task",
    "advance_in_progress": "finish or close the active advancement iterator",
}


class ProviderError(ValueError):
    """Fixed diagnostic codes and safe locations; never supplied data."""

    def __init__(self, code: str, path: ErrorPath = ()) -> None:
        self.code = code
        self.path = path
        self.message = _REASONS[code]
        super().__init__(f"{code}: {self.message}")


def json_snapshot(value: object, depth: int = 0, active: frozenset[int] = frozenset()) -> object:
    """Validate before delegation so legacy validators never see non-JSON input."""
    if depth > 24:
        raise ProviderError("invalid_json")
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) not in (list, dict) or id(value) in active:
        raise ProviderError("invalid_json")
    active = active | {id(value)}
    if type(value) is list:
        return [json_snapshot(v, depth + 1, active) for v in cast(list[object], value)]
    data = cast(dict[object, object], value)
    if any(type(k) is not str for k in data):
        raise ProviderError("invalid_json")
    return {cast(str, k): json_snapshot(v, depth + 1, active) for k, v in data.items()}


def fields(value: object, names: tuple[str, ...], code: str) -> dict[str, object]:
    if type(value) is not dict:
        raise ProviderError(code)
    data = cast(dict[str, object], value)
    for name in names:
        if name not in data:
            raise ProviderError(code, (name,))
    if data.keys() != set(names):
        raise ProviderError(code, ("<unknown>",))
    return data


def integer(value: object, code: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ProviderError(code)
    return value


def token(value: object, code: str) -> str:
    if type(value) is not str or not _TOKEN.fullmatch(value):
        raise ProviderError(code)
    return value


def canonical(value: object, code: str) -> str:
    if type(value) is not str or not CANONICAL_ID_PATTERN.fullmatch(value):
        raise ProviderError(code)
    return value


def envelope(data: dict[str, object], code: str) -> None:
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ProviderError(code, ("schema_version",))
    if data["provider"] != "mock":
        raise ProviderError(code, ("provider",))
    canonical(data["provider_instance_id"], code)


def encode(value: object) -> str:
    return json.dumps(json_snapshot(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True, slots=True)
class DeviceRegistration:
    home_id: str
    device_id: str
    supported_capabilities: tuple[tuple[str, int], ...]
    binding: ProviderBinding

    @classmethod
    def from_dict(cls, value: object, *, configuration: MockConfiguration) -> DeviceRegistration:
        """Read a discovery record against the explicit trusted configuration."""
        code = "invalid_configuration"
        d = fields(
            json_snapshot(value),
            ("home_id", "device_id", "supported_capabilities", "binding"),
            code,
        )
        registered = configuration.registration(d["home_id"], d["device_id"])
        # Strict JSON equality includes the support entry types (bool is not int).
        if encode(d) != encode(registered.to_dict()):
            raise ProviderError(code)
        return registered

    def to_dict(self) -> dict[str, object]:
        return {
            "home_id": self.home_id,
            "device_id": self.device_id,
            "supported_capabilities": [
                {"capability_id": k, "capability_version": v}
                for k, v in self.supported_capabilities
            ],
            "binding": self.binding.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class NormalizedInput:
    _json: str

    @classmethod
    def from_dict(cls, value: object, *, configuration: MockConfiguration) -> NormalizedInput:
        code = "invalid_input"
        d = fields(
            json_snapshot(value),
            (
                "schema_version",
                "provider",
                "provider_instance_id",
                "home_id",
                "device_id",
                "kind",
                "capability_id",
                "capability_version",
                "member",
                "payload",
                "correlation",
            ),
            code,
        )
        envelope(d, code)
        if d["provider_instance_id"] != configuration.provider_instance_id:
            raise ProviderError(code, ("provider_instance_id",))
        reg = configuration.registration(d["home_id"], d["device_id"])
        kind = d["kind"]
        if type(kind) is not str or kind not in ("property", "availability", "event"):
            raise ProviderError(code, ("kind",))
        corr = d["correlation"]
        if corr is not None:
            corr = fields(corr, ("task_id", "trace_id"), code)
            token(corr["task_id"], code)
            token(corr["trace_id"], code)
        try:
            if kind == "availability":
                if any(d[k] is not None for k in ("capability_id", "capability_version", "member")):
                    raise ProviderError(code)
                d["payload"] = Availability.from_dict(d["payload"]).to_dict()
            else:
                version = integer(d["capability_version"], code, 1)
                if (d["capability_id"], version) not in reg.supported_capabilities:
                    raise ProviderError("unsupported")
                desc = configuration.catalogue.get(d["capability_id"], version)
                if kind == "property":
                    observation = Observation.from_dict(d["payload"])
                    if type(d["member"]) is not str or d["member"] not in dict(desc.properties):
                        raise ProviderError("unsupported")
                    if observation.status == "known":
                        desc.validate_payload("property", d["member"], observation.value)
                    d["payload"] = observation.to_dict()
                else:
                    event = fields(d["payload"], ("value", "ordering"), code)
                    desc.validate_payload("event", d["member"], event["value"])
                    event["ordering"] = Ordering.from_dict(event["ordering"]).to_dict()
        except (CapabilityError, StateError):
            raise ProviderError(code, ("payload",)) from None
        return cls(encode(d))

    def to_dict(self) -> dict[str, object]:
        return cast(dict[str, object], json.loads(self._json))


@dataclass(frozen=True, slots=True)
class ProviderOutcome:
    provider_instance_id: str
    result: ActionResult

    @classmethod
    def from_dict(cls, value: object) -> ProviderOutcome:
        code = "invalid_outcome"
        d = fields(
            json_snapshot(value),
            ("schema_version", "provider", "provider_instance_id", "result"),
            code,
        )
        envelope(d, code)
        try:
            result = ActionResult.from_dict(d["result"])
        except ActionError:
            raise ProviderError(code, ("result",)) from None
        return cls(cast(str, d["provider_instance_id"]), result)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "provider": "mock",
            "provider_instance_id": self.provider_instance_id,
            "result": self.result.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class ScriptedDelivery:
    delay_ms: int
    input: NormalizedInput | None
    outcome: ProviderOutcome | None

    def to_dict(self) -> dict[str, object]:
        return {
            "delay_ms": self.delay_ms,
            "input": None if self.input is None else self.input.to_dict(),
            "outcome": None if self.outcome is None else self.outcome.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class AttemptScript:
    task_id: str
    attempt_id: str
    deliveries: tuple[ScriptedDelivery, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "attempt_id": self.attempt_id,
            "deliveries": [d.to_dict() for d in self.deliveries],
        }


@dataclass(frozen=True, slots=True)
class MockConfiguration:
    provider_instance_id: str
    inventory: Inventory
    bindings: BindingCollection
    catalogue: CapabilityCatalogue
    devices: tuple[DeviceRegistration, ...]
    scenarios: tuple[AttemptScript, ...]

    @classmethod
    def from_dict(cls, value: object) -> MockConfiguration:
        code = "invalid_configuration"
        d = fields(
            json_snapshot(value),
            (
                "schema_version",
                "provider",
                "provider_instance_id",
                "inventory",
                "bindings",
                "catalogue",
                "devices",
                "scenarios",
            ),
            code,
        )
        envelope(d, code)
        instance = cast(str, d["provider_instance_id"])
        try:
            inventory = Inventory.from_dict(d["inventory"])
            bindings = BindingCollection.from_dict(d["bindings"], inventory=inventory.to_dict())
            catalogue = CapabilityCatalogue.from_dict(d["catalogue"])
        except (InventoryError, BindingError, CapabilityError):
            raise ProviderError(code) from None
        if type(d["devices"]) is not list or type(d["scenarios"]) is not list:
            raise ProviderError(code)
        bound = {b.device_id: b for b in bindings.bindings}
        if any(b.provider != "mock" or b.provider_instance_id != instance for b in bound.values()):
            raise ProviderError(code, ("bindings",))
        registrations: list[DeviceRegistration] = []
        seen: set[str] = set()
        for raw in cast(list[object], d["devices"]):
            reg = fields(raw, ("home_id", "device_id", "supported_capabilities"), code)
            device = canonical(reg["device_id"], code)
            if reg["home_id"] != inventory.home.id or device not in bound or device in seen:
                raise ProviderError(code, ("devices",))
            seen.add(device)
            support = reg["supported_capabilities"]
            if type(support) is not list:
                raise ProviderError(code)
            pairs: list[tuple[str, int]] = []
            properties: set[str] = set()
            for raw_pair in cast(list[object], support):
                pair = fields(raw_pair, ("capability_id", "capability_version"), code)
                version = integer(pair["capability_version"], code, 1)
                try:
                    descriptor = catalogue.get(pair["capability_id"], version)
                except CapabilityError:
                    raise ProviderError(code, ("devices",)) from None
                key = (descriptor.capability_id, version)
                names = set(dict(descriptor.properties))
                if key in pairs or names & properties:
                    raise ProviderError(code, ("devices",))
                properties |= names
                pairs.append(key)
            registrations.append(
                DeviceRegistration(inventory.home.id, device, tuple(pairs), bound[device])
            )
        if seen != bound.keys():
            raise ProviderError(code, ("bindings",))
        partial = cls(instance, inventory, bindings, catalogue, tuple(registrations), ())
        scripts: list[AttemptScript] = []
        script_keys: set[tuple[str, str]] = set()
        for raw in cast(list[object], d["scenarios"]):
            s = fields(raw, ("task_id", "attempt_id", "deliveries"), code)
            task_id, attempt_id = token(s["task_id"], code), token(s["attempt_id"], code)
            if (task_id, attempt_id) in script_keys or type(s["deliveries"]) is not list:
                raise ProviderError(code, ("scenarios",))
            script_keys.add((task_id, attempt_id))
            items: list[ScriptedDelivery] = []
            for raw_item in cast(list[object], s["deliveries"]):
                item = fields(raw_item, ("delay_ms", "input", "outcome"), code)
                delay = integer(item["delay_ms"], code)
                if (item["input"] is None) == (item["outcome"] is None):
                    raise ProviderError(code, ("scenarios",))
                inp = (
                    None
                    if item["input"] is None
                    else NormalizedInput.from_dict(item["input"], configuration=partial)
                )
                out = (
                    None if item["outcome"] is None else ProviderOutcome.from_dict(item["outcome"])
                )
                if out is not None:
                    if (
                        out.provider_instance_id != instance
                        or out.result.task_id != task_id
                        or out.result.state not in ("running", "acknowledged", "failed")
                        or (
                            out.result.state == "running"
                            and (
                                out.result.evidence is None or out.result.evidence["kind"] != "ack"
                            )
                        )
                    ):
                        raise ProviderError("invalid_outcome")
                if inp is not None:
                    corr = inp.to_dict()["correlation"]
                    if corr is not None and cast(dict[str, object], corr)["task_id"] != task_id:
                        raise ProviderError("invalid_input")
                items.append(ScriptedDelivery(delay, inp, out))
            scripts.append(AttemptScript(task_id, attempt_id, tuple(items)))
        return cls(instance, inventory, bindings, catalogue, tuple(registrations), tuple(scripts))

    def registration(self, home_id: object, device_id: object) -> DeviceRegistration:
        for item in self.devices:
            if (item.home_id, item.device_id) == (home_id, device_id):
                return item
        raise ProviderError("unsupported")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "provider": "mock",
            "provider_instance_id": self.provider_instance_id,
            "inventory": self.inventory.to_dict(),
            "bindings": self.bindings.to_dict(),
            "catalogue": self.catalogue.to_dict(),
            "devices": [
                {
                    "home_id": r.home_id,
                    "device_id": r.device_id,
                    "supported_capabilities": [
                        {"capability_id": k, "capability_version": v}
                        for k, v in r.supported_capabilities
                    ],
                }
                for r in self.devices
            ],
            "scenarios": [s.to_dict() for s in self.scenarios],
        }
