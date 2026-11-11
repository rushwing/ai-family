"""REQ-038 private offline HA operation descriptions; resolution grants no authority."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Literal, NoReturn, cast

from state_schema.capability import CapabilityCatalogue
from state_schema.home_inventory import Inventory
from state_schema.initial_capabilities import load_initial_capabilities
from state_schema.provider_binding import BindingCollection

from .action_validation import ActionValidator
from .action_validation import Code as ValidationCode
from .ha_mapping import _canonical, _json

__all__ = ["ActionResolver", "ActionResolutionResult", "ActionResolutionError"]

Code = ValidationCode | Literal[
    "missing_binding", "provider_mismatch", "unsupported_operation",
    "mapping_uninitialized", "invalid_provider_mapping",
]


class ActionResolutionError(ValueError):
    """Fixed construction diagnostic; underlying data/chains are not exported."""

    def __init__(self) -> None:
        super().__init__("invalid_configuration")


@dataclass(frozen=True, slots=True, repr=False)
class ActionResolutionResult:
    """Internal typed record. Only resolve supplies checked private plans."""

    failure_code: Code | None
    _payload: str | None = None

    @property
    def status(self) -> Literal["resolved", "rejected"]:
        return "resolved" if self.failure_code is None else "rejected"

    def to_redacted_dict(self) -> dict[str, object]:
        return {"status": self.status, "failure_code": self.failure_code}

    def for_adapter(self) -> dict[str, object]:
        payload = {"request": None, "operation": None} if self._payload is None else (
            json.loads(self._payload))
        return {**self.to_redacted_dict(), **payload}

    def __repr__(self) -> str:
        return "ActionResolutionResult()"

    def __reduce__(self) -> NoReturn:
        raise TypeError("action_resolution_result_serialization_forbidden")


def _expected_mapping(capability: str, instance: str, entity: str) -> dict[str, object]:
    if capability == "home.switchable":
        prop = "is_on"
        actions: dict[str, object] = {"set_on": {
            "domain": "switch", "selector": "is_on",
            "services": {"true": "turn_on", "false": "turn_off"}, "service_data": {},
        }}
        source, attribute = "state", None
    else:
        prop = "position_percent"
        actions = {"set_position": {
            "domain": "cover", "service": "set_cover_position",
            "parameters": {"position": {"input": "position_percent"}},
        }}
        source, attribute = "attribute", "current_position"
    return {"provider": "ha", "provider_instance_id": instance, "entity_id": entity,
            "properties": {prop: {"source": source, "attribute": attribute}}, "actions": actions}


@dataclass(frozen=True, slots=True, init=False, repr=False)
class ActionResolver:
    """One immutable configured home/HA instance. No provider execution surface."""

    _instance: str
    _validator: ActionValidator
    _bindings: tuple[tuple[str, str], ...]
    _entries: tuple[tuple[str, str, int, str, str], ...]
    _descriptors: tuple[tuple[str, str], ...]

    def __init__(self, *, registered_inventory: object, bindings: object,
                 capability_projection: object, provider_instance_id: object,
                 max_input_bytes: object = 65536) -> None:
        if hasattr(self, "_instance"):
            raise AttributeError("immutable_action_resolver")
        failed = False
        entries: list[tuple[str, str, int, str, str]] = []
        metadata: list[dict[str, object]] = []
        try:
            instance = _canonical(provider_instance_id)
            inventory = Inventory.from_dict(json.loads(_json(registered_inventory)))
            collection = BindingCollection.from_dict(json.loads(_json(bindings)),
                                                     inventory=inventory.to_dict())
            projection = json.loads(_json(capability_projection))
            if (type(projection) is not dict or set(projection) != {"rules_version", "devices"}
                    or type(projection["rules_version"]) is not int
                    or projection["rules_version"] != 1 or type(projection["devices"]) is not list):
                raise ValueError
            for record in projection["devices"]:
                if (type(record) is not dict or set(record) != {
                        "home_id", "device_id", "capabilities"}
                        or type(record["capabilities"]) is not list):
                    raise ValueError
                descriptors = []
                for entry in record["capabilities"]:
                    if (type(entry) is not dict or set(entry) != {"descriptor", "provider_mapping"}
                            or (entry["provider_mapping"] is not None
                                and type(entry["provider_mapping"]) is not dict)):
                        raise ValueError
                    descriptor = CapabilityCatalogue.from_dict({
                        "schema_version": 1, "capabilities": [entry["descriptor"]],
                    }).capabilities[0]
                    descriptors.append(descriptor.to_dict())
                    entries.append((record["device_id"], descriptor.capability_id,
                                    descriptor.capability_version, _json(descriptor.to_dict()),
                                    _json(entry["provider_mapping"])))
                metadata.append({"home_id": record["home_id"], "device_id": record["device_id"],
                                 "capabilities": descriptors})
            validator = ActionValidator(registered_inventory=inventory.to_dict(),
                                        capabilities=metadata, max_input_bytes=max_input_bytes)
            supported = tuple((item.capability_id, _json(item.to_dict()))
                              for item in load_initial_capabilities().capabilities
                              if item.capability_id in ("home.switchable", "home.positionable"))
            bound = tuple((item.device_id, _json(item.to_dict())) for item in collection.bindings)
        except Exception:
            failed = True
        if failed:
            raise ActionResolutionError()
        object.__setattr__(self, "_instance", instance)
        object.__setattr__(self, "_validator", validator)
        object.__setattr__(self, "_bindings", bound)
        object.__setattr__(self, "_entries", tuple(entries))
        object.__setattr__(self, "_descriptors", supported)

    def resolve(self, request: object) -> ActionResolutionResult:
        checked = self._validator.validate(request)
        if checked.failure_code is not None:
            return ActionResolutionResult(checked.failure_code)
        canonical = cast(dict[str, object], checked.to_dict()["request"])
        device = canonical["device_id"]
        binding_json = next((value for identity, value in self._bindings
                             if identity == device), None)
        if binding_json is None:
            return ActionResolutionResult("missing_binding")
        binding = json.loads(binding_json)
        if binding["provider"] != "ha" or binding["provider_instance_id"] != self._instance:
            return ActionResolutionResult("provider_mismatch")
        capability = canonical["capability_id"]
        version = canonical["capability_version"]
        entry = next(row for row in self._entries if row[:3] == (device, capability, version))
        supported = dict(self._descriptors).get(cast(str, capability))
        if supported is None or entry[3] != supported:
            return ActionResolutionResult("unsupported_operation")
        mapping = json.loads(entry[4])
        if mapping is None:
            return ActionResolutionResult("mapping_uninitialized")
        entity = mapping.get("entity_id")
        domain = "switch" if capability == "home.switchable" else "cover"
        if (type(entity) is not str
                or re.fullmatch(domain + r"\.[a-z0-9_]+", entity, re.ASCII) is None
                or entity not in binding["mapping"]["entity_ids"]
                or mapping != _expected_mapping(cast(str, capability), self._instance, entity)):
            return ActionResolutionResult("invalid_provider_mapping")
        arguments = cast(dict[str, object], canonical["arguments"])
        if capability == "home.switchable":
            service = "turn_on" if arguments["is_on"] else "turn_off"
            service_data: dict[str, object] = {}
        else:
            service = "set_cover_position"
            service_data = {"position": arguments["position_percent"]}
        operation = {"provider": "ha", "provider_instance_id": self._instance, "domain": domain,
                     "service": service, "target": {"entity_id": entity},
                     "service_data": service_data}
        return ActionResolutionResult(None, _json({"request": canonical, "operation": operation}))

    def __repr__(self) -> str:
        return "ActionResolver()"

    def __reduce__(self) -> NoReturn:
        raise TypeError("action_resolver_serialization_forbidden")
