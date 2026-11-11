"""REQ-037 pure semantic preflight; validity never authorizes physical dispatch."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal, NoReturn

from state_schema.action_contracts import ActionRequest
from state_schema.capability import CapabilityCatalogue, CapabilityError
from state_schema.home_inventory import Inventory

from .ha_mapping import _json

__all__ = ["ActionValidator", "ActionValidationResult", "ActionValidationError"]

Code = Literal[
    "invalid_request", "input_too_large", "unknown_home", "unknown_device",
    "capabilities_uninitialized", "unknown_capability", "unsupported_capability_version",
    "read_only_capability", "unknown_action", "invalid_arguments",
]


class ActionValidationError(ValueError):
    """Fixed construction diagnostic, raised outside underlying exception handlers."""

    def __init__(self) -> None:
        super().__init__("invalid_configuration")


@dataclass(frozen=True, slots=True, repr=False)
class ActionValidationResult:
    """Internal typed record; to_dict is the supported detached export."""

    failure_code: Code | None
    _request_json: str | None = None

    @property
    def status(self) -> Literal["valid", "rejected"]:
        return "valid" if self.failure_code is None else "rejected"

    def to_dict(self) -> dict[str, object]:
        return {"status": self.status, "failure_code": self.failure_code,
                "request": None if self._request_json is None else json.loads(self._request_json)}

    def __repr__(self) -> str:
        return "ActionValidationResult()"

    def __reduce__(self) -> NoReturn:
        raise TypeError("action_validation_result_serialization_forbidden")


@dataclass(frozen=True, slots=True, init=False, repr=False)
class ActionValidator:
    """Immutable one-home metadata; no requester policy or provider dependency."""

    _home: str
    _devices: frozenset[str]
    _catalogues: tuple[tuple[str, str], ...]
    _max_input_bytes: int

    def __init__(self, *, registered_inventory: object, capabilities: object,
                 max_input_bytes: object = 65536) -> None:
        if hasattr(self, "_home"):
            raise AttributeError("immutable_action_validator")
        failed = False
        records: list[tuple[str, str]] = []
        try:
            if type(max_input_bytes) is not int or not 0 < max_input_bytes <= 16777216:
                raise ValueError
            inventory = Inventory.from_dict(json.loads(_json(registered_inventory)))
            devices = frozenset(d.id for d in inventory.devices)
            raw = json.loads(_json(capabilities))
            if type(raw) is not list:
                raise ValueError
            seen: set[str] = set()
            for record in raw:
                if type(record) is not dict or set(record) != {
                    "home_id", "device_id", "capabilities",
                }:
                    raise ValueError
                home, device = record["home_id"], record["device_id"]
                if (type(home) is not str or home != inventory.home.id
                        or type(device) is not str or device not in devices or device in seen):
                    raise ValueError
                catalogue = CapabilityCatalogue.from_dict(
                    {"schema_version": 1, "capabilities": record["capabilities"]})
                records.append((device, _json(catalogue.to_dict())))
                seen.add(device)
        except Exception:
            failed = True
        if failed:
            raise ActionValidationError()
        object.__setattr__(self, "_home", inventory.home.id)
        object.__setattr__(self, "_devices", devices)
        object.__setattr__(self, "_catalogues", tuple(sorted(records)))
        object.__setattr__(self, "_max_input_bytes", max_input_bytes)

    def __repr__(self) -> str:
        return "ActionValidator()"

    def __reduce__(self) -> NoReturn:
        raise TypeError("action_validator_serialization_forbidden")

    def validate(self, request: object) -> ActionValidationResult:
        """Validate raw canonical JSON; never call providers or grant permission."""
        try:
            encoded = _json(request)
            if len(encoded.encode("utf-8")) > self._max_input_bytes:
                return ActionValidationResult("input_too_large")
            parsed = ActionRequest.from_dict(json.loads(encoded))
        except Exception:
            return ActionValidationResult("invalid_request")
        identity = parsed.identity
        if identity.home_id != self._home:
            return ActionValidationResult("unknown_home")
        if identity.device_id not in self._devices:
            return ActionValidationResult("unknown_device")
        catalogue_json = next((value for device, value in self._catalogues
                               if device == identity.device_id), None)
        if catalogue_json is None:
            return ActionValidationResult("capabilities_uninitialized")
        catalogue = CapabilityCatalogue.from_dict(json.loads(catalogue_json))
        matches = [item for item in catalogue.capabilities
                   if item.capability_id == identity.capability_id]
        if not matches:
            return ActionValidationResult("unknown_capability")
        descriptor = next((item for item in matches
                           if item.capability_version == identity.capability_version), None)
        if descriptor is None:
            return ActionValidationResult("unsupported_capability_version")
        if (descriptor.properties
                and all(prop.read_only for _, prop in descriptor.properties)):
            return ActionValidationResult("read_only_capability")
        if identity.action_id not in dict(descriptor.actions):
            return ActionValidationResult("unknown_action")
        try:
            descriptor.validate_payload("action_input", identity.action_id, parsed.arguments)
        except CapabilityError:
            return ActionValidationResult("invalid_arguments")
        return ActionValidationResult(None, json.dumps(parsed.to_dict(), allow_nan=False))
