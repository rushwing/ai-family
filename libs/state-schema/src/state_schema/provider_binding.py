"""Strict offline ProviderBinding contracts, separate from canonical inventory.

Factories validate external JSON. Direct constructors are typed internal records,
not a reference-integrity boundary. Bindings describe resource mappings; they
provide no provider connection, availability, permission or dispatch behavior.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, cast

from .home_inventory import ErrorPath, Inventory, InventoryError

Provider = Literal["ha", "mock"]
_ID = re.compile(r"[a-z][a-z0-9_-]{0,63}", re.ASCII)


class BindingError(ValueError):
    """Deterministic structured location and reason without supplied values."""

    def __init__(self, path: ErrorPath, message: str) -> None:
        self.path = path
        self.message = message
        location = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}" for part in path
        )
        super().__init__(f"{location}: {message}")


def _object(
    value: object, path: ErrorPath, required: tuple[str, ...], optional: tuple[str, ...] = ()
) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise BindingError(path, "expected an object with string field names")
    data = cast(dict[str, object], value)
    for key in required:
        if key not in data:
            raise BindingError((*path, key), "required field is missing")
    unknown = sorted(data.keys() - set(required) - set(optional))
    if unknown:
        raise BindingError((*path, unknown[0]), "unknown field")
    return data


def _text(value: object, path: ErrorPath) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BindingError(path, "expected a nonempty string")
    if value != value.strip():
        raise BindingError(path, "must be trimmed; leading/trailing whitespace is not allowed")
    return value


def _id(value: object, path: ErrorPath) -> str:
    if not isinstance(value, str) or _ID.fullmatch(value) is None:
        raise BindingError(path, "expected a canonical ID matching ^[a-z][a-z0-9_-]{0,63}$")
    return value


@dataclass(frozen=True, slots=True)
class HAMapping:
    entity_ids: tuple[str, ...]
    device_registry_id: str | None = None

    @classmethod
    def from_dict(cls, value: object, path: ErrorPath = ()) -> HAMapping:
        data = _object(value, path, ("entity_ids",), ("device_registry_id",))
        entities = data["entity_ids"]
        entity_path = (*path, "entity_ids")
        if not isinstance(entities, list):
            raise BindingError(entity_path, "expected a list")
        if not entities:
            raise BindingError(entity_path, "must contain at least one entity")
        result: list[str] = []
        seen: set[str] = set()
        for index, raw in enumerate(entities):
            item = _text(raw, (*entity_path, index))
            if item in seen:
                raise BindingError((*entity_path, index), "duplicate entity identifier")
            seen.add(item)
            result.append(item)
        registry = data.get("device_registry_id")
        return cls(
            tuple(result),
            None if registry is None else _text(registry, (*path, "device_registry_id")),
        )

    def to_dict(self) -> dict[str, object]:
        return {"entity_ids": list(self.entity_ids), "device_registry_id": self.device_registry_id}


@dataclass(frozen=True, slots=True)
class MockMapping:
    device_key: str

    @classmethod
    def from_dict(cls, value: object, path: ErrorPath = ()) -> MockMapping:
        data = _object(value, path, ("device_key",))
        return cls(_text(data["device_key"], (*path, "device_key")))

    def to_dict(self) -> dict[str, object]:
        return {"device_key": self.device_key}


@dataclass(frozen=True, slots=True)
class ProviderBinding:
    home_id: str
    device_id: str
    provider: Provider
    provider_instance_id: str
    mapping: HAMapping | MockMapping

    @classmethod
    def from_dict(cls, value: object, path: ErrorPath = ()) -> ProviderBinding:
        """Validate shape only; use BindingCollection for inventory references."""
        data = _object(
            value, path, ("home_id", "device_id", "provider", "provider_instance_id", "mapping")
        )
        home_id = _id(data["home_id"], (*path, "home_id"))
        device_id = _id(data["device_id"], (*path, "device_id"))
        provider = _text(data["provider"], (*path, "provider"))
        if provider not in ("ha", "mock"):
            raise BindingError((*path, "provider"), "unsupported provider; expected ha or mock")
        instance = _text(data["provider_instance_id"], (*path, "provider_instance_id"))
        mapping = (
            HAMapping.from_dict(data["mapping"], (*path, "mapping"))
            if provider == "ha"
            else MockMapping.from_dict(data["mapping"], (*path, "mapping"))
        )
        return cls(home_id, device_id, cast(Provider, provider), instance, mapping)

    def to_dict(self) -> dict[str, object]:
        """Return a detached JSON snapshot with explicit mapping defaults."""
        return {
            "home_id": self.home_id,
            "device_id": self.device_id,
            "provider": self.provider,
            "provider_instance_id": self.provider_instance_id,
            "mapping": self.mapping.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class BindingCollection:
    schema_version: Literal[1]
    bindings: tuple[ProviderBinding, ...]

    @classmethod
    def from_dict(cls, value: object, *, inventory: object) -> BindingCollection:
        """Validate shape, inventory references and local collection uniqueness."""
        data = _object(value, (), ("schema_version", "bindings"))
        if type(data["schema_version"]) is not int or data["schema_version"] != 1:
            raise BindingError(("schema_version",), "expected supported integer schema version 1")
        if not isinstance(data["bindings"], list):
            raise BindingError(("bindings",), "expected a list")
        try:
            canonical = Inventory.from_dict(inventory)
        except InventoryError as error:
            # Inventory diagnostics may include private label/ID values. Preserve
            # the location, suppress the original message and exception chain.
            raise BindingError(("inventory", *error.path), "invalid canonical inventory") from None
        bindings = tuple(
            ProviderBinding.from_dict(raw, ("bindings", index))
            for index, raw in enumerate(data["bindings"])
        )
        devices = {device.id for device in canonical.devices}
        bound: set[str] = set()
        resources: set[tuple[Provider, str, str]] = set()
        for index, binding in enumerate(bindings):
            path: ErrorPath = ("bindings", index)
            if binding.home_id != canonical.home.id:
                raise BindingError((*path, "home_id"), "must reference this inventory Home")
            if binding.device_id not in devices:
                raise BindingError((*path, "device_id"), "unknown Device in this inventory Home")
            if binding.device_id in bound:
                raise BindingError((*path, "device_id"), "duplicate canonical Device binding")
            bound.add(binding.device_id)
            mapping = binding.mapping
            resource_paths: tuple[tuple[str, ErrorPath], ...]
            if isinstance(mapping, HAMapping):
                resource_paths = tuple(
                    (entity, (*path, "mapping", "entity_ids", member))
                    for member, entity in enumerate(mapping.entity_ids)
                )
            else:
                resource_paths = ((mapping.device_key, (*path, "mapping", "device_key")),)
            for resource, resource_path in resource_paths:
                key = (binding.provider, binding.provider_instance_id, resource)
                if key in resources:
                    raise BindingError(
                        resource_path, "resource already bound in this provider instance"
                    )
                resources.add(key)
        return cls(1, bindings)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "bindings": [binding.to_dict() for binding in self.bindings],
        }


def validate_binding(data: object) -> dict[str, object]:
    """Validate and normalize one binding's shape without reference integrity."""
    return ProviderBinding.from_dict(data).to_dict()


def validate_bindings(data: object, *, inventory: object) -> dict[str, object]:
    """Validate a separate collection against an unmodified JSON inventory snapshot."""
    return BindingCollection.from_dict(data, inventory=inventory).to_dict()
