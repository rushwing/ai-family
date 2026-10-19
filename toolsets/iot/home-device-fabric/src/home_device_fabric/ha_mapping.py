"""Pure HA registry projection; canonical identities are assigned by trusted callers.

No allocation, persistence, capabilities, state publication or provider actions.
Private inputs/results require explicit export; ordinary diagnostics are finite.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import NoReturn, cast

from state_schema.home_inventory import CANONICAL_ID_PATTERN, Home, Inventory
from state_schema.provider_binding import BindingCollection

__all__ = ["HARegistryMapper", "HAMappingResult", "HAMappingError"]

_CODES = frozenset(
    {
        "invalid_configuration",
        "invalid_discovery",
        "input_limit",
        "invalid_projection",
        "internal_error",
    }
)
_COMPONENTS = ("devices", "entities", "areas", "states")
_COUNT_KEYS = (
    "areas",
    "devices",
    "bindings",
    "disabled_devices",
    "disabled_entities",
    "unassigned_areas",
    "unassigned_devices",
    "unassigned_entities",
    "orphan_entities",
    "unbound_devices",
    "unresolved_areas",
    "ignored_states",
)


class HAMappingError(Exception):
    """Finite immutable diagnosis without submitted values or raw exception chains."""

    __slots__ = ("_code",)
    _code: str

    def __init__(self, code: str):
        if type(code) is not str or code not in _CODES:
            raise ValueError("invalid_diagnostic")
        if hasattr(self, "_code"):
            raise AttributeError("immutable_mapping_error")
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
        return f"HAMappingError({self.code!r})"

    def __setattr__(self, name: str, value: object) -> None:
        if name in (
            "__traceback__",
            "__context__",
            "__cause__",
            "__suppress_context__",
            "__notes__",
        ):
            super().__setattr__(name, value)
            return
        raise AttributeError("immutable_mapping_error")

    def __delattr__(self, name: str) -> NoReturn:
        raise AttributeError("immutable_mapping_error")

    def __reduce__(self) -> NoReturn:
        raise TypeError("mapping_error_serialization_forbidden")


class _Rejected(ValueError):
    pass


class _Limit(ValueError):
    pass


def _json(value: object) -> str:
    """Validate a bounded plain JSON tree before copying or interpreting fields."""
    pending = [(value, 0)]
    seen: set[int] = set()
    nodes = 0
    scalar_bytes = 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        if depth > 32 or nodes > 200000:
            raise _Limit()
        if type(item) is dict:
            if id(item) in seen:
                raise _Rejected()
            seen.add(id(item))
            if len(item) > 100000:
                raise _Limit()
            for key, child in cast(dict[object, object], item).items():
                if type(key) is not str:
                    raise _Rejected()
                pending.append((key, depth + 1))
                pending.append((child, depth + 1))
        elif type(item) is list:
            if id(item) in seen:
                raise _Rejected()
            seen.add(id(item))
            if len(item) > 200000:
                raise _Limit()
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            scalar_bytes += len(item.encode("utf-8"))
        elif type(item) is float:
            if not math.isfinite(item):
                raise _Rejected()
        elif type(item) is int:
            if item.bit_length() > 4096:
                raise _Limit()
        elif item is not None and type(item) is not bool:
            raise _Rejected()
        if scalar_bytes > 16 * 1024 * 1024:
            raise _Limit()
    text = json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    )
    if len(text.encode("utf-8")) > 16 * 1024 * 1024:
        raise _Limit()
    return text


def _object(value: object, keys: tuple[str, ...] | None = None) -> dict[str, object]:
    if type(value) is not dict:
        raise _Rejected()
    data = cast(dict[str, object], value)
    if keys is not None and set(data) != set(keys):
        raise _Rejected()
    return data


def _text(value: object, limit: int = 512) -> str:
    if type(value) is not str or not value or value != value.strip() or len(value) > limit:
        raise _Rejected()
    return value


def _canonical(value: object) -> str:
    if type(value) is not str or CANONICAL_ID_PATTERN.fullmatch(value) is None:
        raise _Rejected()
    return value


def _optional(record: dict[str, object], field: str) -> str | None:
    value = record.get(field)
    return None if value is None else _text(value)


def _configuration(value: object) -> str:
    text = _json(value)
    data = _object(
        json.loads(text),
        ("schema_version", "home", "provider_instance_id", "area_ids", "device_ids", "entity_ids"),
    )
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise _Rejected()
    home = Home.from_dict(data["home"])
    _canonical(data["provider_instance_id"])
    assigned = {home.id}
    for label in ("area_ids", "device_ids", "entity_ids"):
        mapping = _object(data[label])
        if len(mapping) > 10000:
            raise _Limit()
        for provider, canonical in mapping.items():
            _text(provider)
            identity = _canonical(canonical)
            if identity in assigned:
                raise _Rejected()
            assigned.add(identity)
    return text


def _records(value: object, identity: str) -> dict[str, dict[str, object]]:
    if type(value) is not list:
        raise _Rejected()
    if len(value) > 10000:
        raise _Limit()
    result: dict[str, dict[str, object]] = {}
    for raw in value:
        record = _object(raw)
        key = _text(record.get(identity))
        if key in result:
            raise _Rejected()
        result[key] = record
    return result


def _discovery(value: object) -> dict[str, dict[str, dict[str, object]]]:
    data = _object(json.loads(_json(value)), _COMPONENTS)
    result = {
        label: _records(data[label], identity)
        for label, identity in zip(
            _COMPONENTS, ("id", "entity_id", "area_id", "entity_id"), strict=True
        )
    }
    for label in ("devices", "entities"):
        for record in result[label].values():
            for field in ("area_id", "disabled_by"):
                _optional(record, field)
            if label == "entities":
                _optional(record, "device_id")
            for field in ("name", "name_by_user", "original_name"):
                name = record.get(field)
                if name is not None and (type(name) is not str or len(name) > 512):
                    raise _Rejected()
    for record in result["areas"].values():
        _text(record.get("name"))
    for record in result["states"].values():
        state = record.get("state")
        if type(state) is not str or len(state) > 4096:
            raise _Rejected()
        _object(record.get("attributes"))
    return result


def _name(record: dict[str, object], *fields: str) -> str:
    for field in fields:
        value = record.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "Device"


@dataclass(frozen=True, slots=True, init=False, repr=False)
class HAMappingResult:
    """Internal result record; export consciously to trusted adapter consumers."""

    _inventory: str
    _bindings: str
    _counts: tuple[int, ...]

    def __init__(self, inventory: str, bindings: str, counts: tuple[int, ...]):
        if hasattr(self, "_inventory"):
            raise AttributeError("immutable_mapping_result")
        object.__setattr__(self, "_inventory", inventory)
        object.__setattr__(self, "_bindings", bindings)
        object.__setattr__(self, "_counts", counts)

    def for_adapter(self) -> dict[str, object]:
        return {"inventory": json.loads(self._inventory), "bindings": json.loads(self._bindings)}

    def to_redacted_dict(self) -> dict[str, object]:
        return {"rules_version": 1, "counts": dict(zip(_COUNT_KEYS, self._counts, strict=True))}

    def __repr__(self) -> str:
        return "HAMappingResult(<redacted>)"

    def __reduce__(self) -> NoReturn:
        raise TypeError("raw_mapping_result_serialization_forbidden")


def _project(
    config: dict[str, object], records: dict[str, dict[str, dict[str, object]]]
) -> HAMappingResult:
    home = Home.from_dict(config["home"])
    area_ids = cast(dict[str, str], config["area_ids"])
    device_ids = cast(dict[str, str], config["device_ids"])
    entity_ids = cast(dict[str, str], config["entity_ids"])
    counts = dict.fromkeys(_COUNT_KEYS, 0)
    areas: list[dict[str, object]] = []
    devices: list[dict[str, object]] = []
    bindings: list[dict[str, object]] = []
    for raw_id, record in records["areas"].items():
        if raw_id not in area_ids:
            counts["unassigned_areas"] += 1
            continue
        areas.append(
            {
                "id": area_ids[raw_id],
                "home_id": home.id,
                "name": record["name"],
                "area_type": "other",
                "floor_id": None,
                "labels": [],
                "aliases": [],
            }
        )
    present_areas = {cast(str, area["id"]) for area in areas}
    grouped: dict[str, list[str]] = {}
    standalone: list[str] = []
    for raw_id, record in records["entities"].items():
        if record.get("disabled_by") is not None:
            counts["disabled_entities"] += 1
            continue
        parent = cast(str | None, record.get("device_id"))
        if parent is not None:
            device = records["devices"].get(parent)
            if device is None or parent not in device_ids or device.get("disabled_by") is not None:
                counts["orphan_entities"] += 1
                continue
            grouped.setdefault(parent, []).append(raw_id)
        elif raw_id in entity_ids:
            standalone.append(raw_id)
        else:
            counts["unassigned_entities"] += 1

    def add(
        identity: str,
        record: dict[str, object],
        members: list[str],
        registry_id: str | None,
        name: str,
    ) -> None:
        raw_area = cast(str | None, record.get("area_id"))
        area_id = area_ids.get(raw_area) if raw_area is not None else None
        if area_id not in present_areas:
            if raw_area is not None:
                counts["unresolved_areas"] += 1
            area_id = None
        devices.append(
            {"id": identity, "home_id": home.id, "name": name, "area_id": area_id, "labels": []}
        )
        bindings.append(
            {
                "home_id": home.id,
                "device_id": identity,
                "provider": "ha",
                "provider_instance_id": config["provider_instance_id"],
                "mapping": {"entity_ids": sorted(members), "device_registry_id": registry_id},
            }
        )

    for raw_id, record in records["devices"].items():
        if record.get("disabled_by") is not None:
            counts["disabled_devices"] += 1
        elif raw_id not in device_ids:
            counts["unassigned_devices"] += 1
        elif raw_id not in grouped:
            counts["unbound_devices"] += 1
        else:
            add(
                device_ids[raw_id],
                record,
                grouped[raw_id],
                raw_id,
                _name(record, "name_by_user", "name"),
            )
    for raw_id in standalone:
        record = records["entities"][raw_id]
        add(entity_ids[raw_id], record, [raw_id], None, _name(record, "name", "original_name"))
    inventory = Inventory.from_dict(
        {
            "schema_version": 1,
            "home": config["home"],
            "floors": [],
            "labels": [],
            "area_groups": [],
            "areas": sorted(areas, key=lambda item: cast(str, item["id"])),
            "devices": sorted(devices, key=lambda item: cast(str, item["id"])),
        }
    ).to_dict()
    bound = BindingCollection.from_dict(
        {
            "schema_version": 1,
            "bindings": sorted(bindings, key=lambda item: cast(str, item["device_id"])),
        },
        inventory=inventory,
    ).to_dict()
    mapped_entities = {member for members in grouped.values() for member in members}
    mapped_entities.update(standalone)
    counts.update(
        areas=len(areas),
        devices=len(devices),
        bindings=len(bindings),
        ignored_states=len(set(records["states"]) - mapped_entities),
    )
    return HAMappingResult(
        _json(inventory), _json(bound), tuple(counts[label] for label in _COUNT_KEYS)
    )


@dataclass(frozen=True, slots=True, init=False, repr=False)
class HARegistryMapper:
    """One immutable explicit identity configuration; each map is a fresh projection."""

    _configuration: str

    def __init__(self, configuration: object):
        if hasattr(self, "_configuration"):
            raise AttributeError("immutable_mapper")
        failure: str | None = None
        try:
            value = _configuration(configuration)
        except _Limit:
            failure = "input_limit"
        except Exception:
            failure = "invalid_configuration"
        if failure is not None:
            raise HAMappingError(failure)
        object.__setattr__(self, "_configuration", value)

    def map(self, discovery: object) -> HAMappingResult:
        failure: str | None = None
        try:
            records = _discovery(discovery)
        except _Limit:
            failure = "input_limit"
        except Exception:
            failure = "invalid_discovery"
        if failure is not None:
            raise HAMappingError(failure)
        try:
            result = _project(json.loads(self._configuration), records)
        except _Limit:
            failure = "input_limit"
        except Exception:
            failure = "invalid_projection"
        if failure is not None:
            raise HAMappingError(failure)
        return result

    def __repr__(self) -> str:
        return "HARegistryMapper(<redacted>)"

    def __reduce__(self) -> NoReturn:
        raise TypeError("raw_mapper_serialization_forbidden")
