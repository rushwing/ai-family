"""Version-1 offline capability descriptions, never provider dispatch (REQ-033)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import NoReturn, cast

from state_schema.home_inventory import Inventory
from state_schema.initial_capabilities import load_initial_capabilities
from state_schema.provider_binding import BindingCollection, HAMapping

from .ha_mapping import _canonical, _discovery, _json, _Limit

__all__ = ["HACapabilityInferrer", "HACapabilityError"]

_CODES = frozenset({
    "invalid_configuration", "invalid_inventory", "invalid_bindings",
    "invalid_discovery", "input_limit", "invalid_projection",
})
_SENSORS = {
    ("temperature", "°C"): ("home.temperature_sensor", "temperature_c"),
    ("humidity", "%"): ("home.humidity_sensor", "relative_humidity_percent"),
    ("power", "W"): ("home.power_meter", "power_w"),
    ("battery", "%"): ("home.battery_powered", "battery_percent"),
}


class HACapabilityError(Exception):
    """Finite immutable diagnosis; submitted data and raw chains are discarded."""

    _code: str

    def __init__(self, code: str):
        if type(code) is not str or code not in _CODES:
            raise ValueError("invalid_diagnostic")
        if hasattr(self, "_code"):
            raise AttributeError("immutable_capability_error")
        object.__setattr__(self, "_code", code)
        super().__init__(code)

    @property
    def code(self) -> str:
        return self._code

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code}

    def __str__(self) -> str:
        return self.code

    def __repr__(self) -> str:
        return f"HACapabilityError({self.code!r})"

    def __setattr__(self, name: str, value: object) -> None:
        if name in (
            "__traceback__", "__context__", "__cause__", "__suppress_context__", "__notes__",
        ):
            super().__setattr__(name, value)
            return
        raise AttributeError("immutable_capability_error")

    def __delattr__(self, name: str) -> NoReturn:
        raise AttributeError("immutable_capability_error")

    def __reduce__(self) -> NoReturn:
        raise TypeError("capability_error_serialization_forbidden")


@dataclass(frozen=True, slots=True, repr=False, init=False)
class _CapabilityResult:
    """Internal frozen snapshot; exports are fresh private adapter JSON."""

    _payload: str
    _counts: tuple[int, int, int, int]

    def __init__(self, payload: str, counts: tuple[int, int, int, int]):
        if hasattr(self, "_payload"):
            raise AttributeError("immutable_capability_result")
        object.__setattr__(self, "_payload", payload)
        object.__setattr__(self, "_counts", counts)

    def for_adapter(self) -> dict[str, object]:
        return cast(dict[str, object], json.loads(self._payload))

    def to_redacted_dict(self) -> dict[str, object]:
        return {"rules_version": 1, "counts": dict(zip(
            ("devices", "capabilities", "unsupported_entities", "ambiguous_entities"),
            self._counts, strict=True,
        ))}

    def __repr__(self) -> str:
        return "HACapabilityResult(<redacted>)"

    def __reduce__(self) -> NoReturn:
        raise TypeError("raw_capability_result_serialization_forbidden")


class _BindingMismatch(ValueError):
    pass


def _rule(entity: str, state: dict[str, object] | None) -> tuple[str, str, str | None] | None:
    if state is None:
        return None
    domain, separator, suffix = entity.partition(".")
    if (not separator or not suffix
            or re.fullmatch(r"[a-z0-9_]+\.[a-z0-9_]+", entity, re.ASCII) is None):
        return None
    attributes = cast(dict[str, object], state["attributes"])
    if domain == "switch":
        return "home.switchable", "is_on", None
    if domain == "cover":
        features = attributes.get("supported_features")
        if type(features) is int and 0 <= features <= 2147483647 and features & 4:
            return "home.positionable", "position_percent", "current_position"
    if domain == "sensor":
        device_class, unit = attributes.get("device_class"), attributes.get("unit_of_measurement")
        if type(device_class) is str and type(unit) is str:
            match = _SENSORS.get((device_class, unit))
            if match is not None:
                return match[0], match[1], None
    return None


def _actions(capability: str) -> dict[str, object]:
    if capability == "home.switchable":
        return {"set_on": {
            "domain": "switch", "selector": "is_on",
            "services": {"true": "turn_on", "false": "turn_off"}, "service_data": {},
        }}
    if capability == "home.positionable":
        return {"set_position": {
            "domain": "cover", "service": "set_cover_position",
            "parameters": {"position": {"input": "position_percent"}},
        }}
    return {}


@dataclass(frozen=True, slots=True, init=False, repr=False)
class HACapabilityInferrer:
    """Explicit construction loads the fixed catalogue; infer is pure and fresh."""

    _instance: str
    _catalogue: str

    def __init__(self, *, provider_instance_id: object):
        if hasattr(self, "_instance"):
            raise AttributeError("immutable_capability_inferrer")
        failure: str | None = None
        try:
            instance = _canonical(provider_instance_id)
            catalogue = _json(load_initial_capabilities().to_dict())
        except Exception:
            failure = "invalid_configuration"
        if failure is not None:
            raise HACapabilityError(failure)
        object.__setattr__(self, "_instance", instance)
        object.__setattr__(self, "_catalogue", catalogue)

    def infer(self, *, inventory: object, bindings: object, discovery: object) -> _CapabilityResult:
        failure: str | None = None
        stage = "invalid_inventory"
        try:
            canonical = Inventory.from_dict(json.loads(_json(inventory)))
            stage = "invalid_bindings"
            collection = BindingCollection.from_dict(
                json.loads(_json(bindings)), inventory=canonical.to_dict(),
            )
            stage = "invalid_discovery"
            records = _discovery(discovery)
        except _Limit:
            failure = "input_limit"
        except Exception:
            failure = stage
        if failure is not None:
            raise HACapabilityError(failure)
        try:
            result = self._project(canonical, collection, records)
        except _Limit:
            failure = "input_limit"
        except _BindingMismatch:
            failure = "invalid_bindings"
        except Exception:
            failure = "invalid_projection"
        if failure is not None:
            raise HACapabilityError(failure)
        return result

    def _project(
        self, inventory: Inventory, bindings: BindingCollection,
        records: dict[str, dict[str, dict[str, object]]],
    ) -> _CapabilityResult:
        catalogue = {
            row["capability_id"]: row
            for row in json.loads(self._catalogue)["capabilities"]
        }
        devices: dict[str, dict[str, object]] = {
            device.id: {"home_id": inventory.home.id, "device_id": device.id, "capabilities": []}
            for device in inventory.devices
        }
        candidates: dict[tuple[str, str], list[dict[str, object]]] = {}
        seen: set[str] = set()
        unsupported = 0
        for binding in bindings.bindings:
            if binding.provider != "ha" or binding.provider_instance_id != self._instance:
                continue
            mapping = binding.mapping
            if not isinstance(mapping, HAMapping):
                raise _BindingMismatch()
            for entity in mapping.entity_ids:
                row = records["entities"].get(entity)
                if (entity in seen or row is None or row.get("disabled_by") is not None
                        or row.get("device_id") != mapping.device_registry_id):
                    raise _BindingMismatch()
                seen.add(entity)
                if mapping.device_registry_id is not None:
                    parent = records["devices"].get(mapping.device_registry_id)
                    if parent is None or parent.get("disabled_by") is not None:
                        raise _BindingMismatch()
                rule = _rule(entity, records["states"].get(entity))
                if rule is None:
                    unsupported += 1
                    continue
                identity, prop, attribute = rule
                candidates.setdefault((binding.device_id, identity), []).append({
                    "descriptor": json.loads(_json(catalogue[identity])),
                    "provider_mapping": {
                        "provider": "ha", "provider_instance_id": self._instance,
                        "entity_id": entity,
                        "properties": {prop: {
                            "source": "state" if attribute is None else "attribute",
                            "attribute": attribute,
                        }},
                        "actions": _actions(identity),
                    },
                })
        ambiguous = capabilities = 0
        for (device, _identity), entries in sorted(candidates.items()):
            if len(entries) != 1:
                ambiguous += len(entries)
                continue
            cast(list[object], devices[device]["capabilities"]).append(entries[0])
            capabilities += 1
        payload = _json({"rules_version": 1, "devices": [devices[key] for key in sorted(devices)]})
        return _CapabilityResult(payload, (len(devices), capabilities, unsupported, ambiguous))

    def __repr__(self) -> str:
        return "HACapabilityInferrer(<redacted>)"

    def __reduce__(self) -> NoReturn:
        raise TypeError("raw_capability_inferrer_serialization_forbidden")
