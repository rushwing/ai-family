"""Pure explicit HA-to-canonical observation adapter (REQ-028).

No clock, epoch allocation, deduplication, storage or capability inference.
Returned DeviceState records are deltas; apply their reported/availability
members through canonical apply_state_update, preserving desired intent.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, NoReturn, cast

from state_schema.canonical_state import DeviceState, Ordering, StateError
from state_schema.home_inventory import CANONICAL_ID_PATTERN
from state_schema.provider_binding import BindingCollection, BindingError, HAMapping

Kind = Literal["switch", "curtain", "temperature"]
Path = tuple[str | int, ...]
_TIME = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})", re.ASCII
)
_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", re.ASCII)
_MEMBERS = {"switch": "is_on", "curtain": "position_percent", "temperature": "temperature_c"}


class HANormalizationError(ValueError):
    """Finite code and fixed schema location; never submitted values/keys."""

    def __init__(self, code: str, path: Path) -> None:
        self.code = code
        self.path = path
        super().__init__(code + ": " + ".".join(str(part) for part in path))


def _object(value: object, path: Path) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise HANormalizationError("malformed_object", path)
    return cast(dict[str, object], value)


def _entity(value: object, path: Path) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise HANormalizationError("malformed_entity", path)
    return value


def _timestamp(value: object) -> str:
    path = ("event", "time_fired")
    if type(value) is not str or _TIME.fullmatch(value) is None:
        raise HANormalizationError("malformed_timestamp", path)
    # fromisoformat normalizes some invalid clock/offset components on some
    # Python versions. Reject them independently before calendar conversion.
    if any(
        int(value[start : start + 2]) > limit for start, limit in ((11, 23), (14, 59), (17, 59))
    ):
        raise HANormalizationError("malformed_timestamp", path)
    if value[-1] != "Z" and (int(value[-5:-3]) > 23 or int(value[-2:]) > 59):
        raise HANormalizationError("malformed_timestamp", path)
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise HANormalizationError("malformed_timestamp", path) from None
    return result.isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True, repr=False)
class _Profile:
    entity: str
    home: str
    device: str
    kind: Kind


@dataclass(frozen=True, slots=True, repr=False, init=False)
class HAEventNormalizer:
    """Validated immutable adapter configuration; repr exposes no mapping data."""

    _profiles: tuple[_Profile, ...]

    def __init__(
        self, *, inventory: object, bindings: object, provider_instance_id: object, profiles: object
    ) -> None:
        if (
            type(provider_instance_id) is not str
            or CANONICAL_ID_PATTERN.fullmatch(provider_instance_id) is None
        ):
            raise HANormalizationError("invalid_configuration", ("provider_instance_id",))
        try:
            collection = BindingCollection.from_dict(bindings, inventory=inventory)
        except BindingError:
            raise HANormalizationError("invalid_configuration", ("bindings",)) from None
        selected: dict[str, tuple[str, str]] = {}
        for binding in collection.bindings:
            if binding.provider != "ha" or binding.provider_instance_id != provider_instance_id:
                continue
            mapping = binding.mapping
            if not isinstance(mapping, HAMapping) or len(mapping.entity_ids) != 1:
                raise HANormalizationError("unsupported_multi_entity", ("bindings",))
            selected[mapping.entity_ids[0]] = (binding.home_id, binding.device_id)
        if type(profiles) is not list:
            raise HANormalizationError("invalid_configuration", ("profiles",))
        result: list[_Profile] = []
        seen: set[str] = set()
        for index, value in enumerate(profiles):
            path: Path = ("profiles", index)
            data = _object(value, path)
            if set(data) != {"entity_id", "kind"}:
                raise HANormalizationError("invalid_configuration", path)
            entity = _entity(data["entity_id"], (*path, "entity_id"))
            kind = data["kind"]
            if type(kind) is not str or kind not in _MEMBERS:
                raise HANormalizationError("unsupported_kind", (*path, "kind"))
            if entity in seen:
                raise HANormalizationError("duplicate_profile", path)
            if entity not in selected:
                raise HANormalizationError("unbound_entity", (*path, "entity_id"))
            seen.add(entity)
            home, device = selected[entity]
            result.append(_Profile(entity, home, device, cast(Kind, kind)))
        if seen != set(selected):
            raise HANormalizationError("missing_profile", ("profiles",))
        object.__setattr__(self, "_profiles", tuple(result))

    def __repr__(self) -> str:
        return "HAEventNormalizer()"

    def __reduce__(self) -> NoReturn:
        raise TypeError("normalizer_serialization_forbidden")

    def normalize(self, event: object, *, ordering: object) -> DeviceState:
        """Convert one decoded subscription event using owner-established order."""
        try:
            order = Ordering.from_dict(ordering).to_dict()
        except StateError:
            raise HANormalizationError("invalid_ordering", ("ordering",)) from None
        frame = _object(event, ("event",))
        if frame.get("event_type") != "state_changed":
            raise HANormalizationError("wrong_event_type", ("event", "event_type"))
        observed = _timestamp(frame.get("time_fired"))
        data = _object(frame.get("data"), ("event", "data"))
        entity = _entity(data.get("entity_id"), ("event", "data", "entity_id"))
        profile = next((item for item in self._profiles if item.entity == entity), None)
        if profile is None:
            raise HANormalizationError("unbound_entity", ("event", "data", "entity_id"))
        for field in ("old_state", "new_state"):
            if field not in data or (data[field] is not None and type(data[field]) is not dict):
                raise HANormalizationError("malformed_state", ("event", "data", field))
        new = data["new_state"]
        reports: dict[str, object] = {}
        availability = "offline"
        if new is not None:
            state = _object(new, ("event", "data", "new_state"))
            if state.get("entity_id") != entity:
                raise HANormalizationError(
                    "identity_mismatch", ("event", "data", "new_state", "entity_id")
                )
            raw = state.get("state")
            if type(raw) is not str:
                raise HANormalizationError(
                    "malformed_state", ("event", "data", "new_state", "state")
                )
            attrs = _object(state.get("attributes"), ("event", "data", "new_state", "attributes"))
            if raw != "unavailable":
                value = None if raw == "unknown" else _convert(profile.kind, raw, attrs)
                availability = "unknown" if raw == "unknown" else "online"
                reports[_MEMBERS[profile.kind]] = {
                    "status": "unknown" if value is None else "known",
                    "value": value,
                    "observed_at": observed,
                    "ordering": order,
                }
        return DeviceState.from_dict(
            {
                "home_id": profile.home,
                "device_id": profile.device,
                "desired_state": None,
                "reported_state": reports,
                "availability": {
                    "status": availability,
                    "observed_at": observed,
                    "ordering": order,
                },
            }
        )


def _convert(kind: Kind, raw: str, attrs: dict[str, object]) -> bool | int | float | None:
    path = ("event", "data", "new_state")
    if kind == "switch":
        if raw not in ("on", "off"):
            raise HANormalizationError("unsupported_state", (*path, "state"))
        return raw == "on"
    if kind == "curtain":
        if raw not in ("open", "closed", "opening", "closing"):
            raise HANormalizationError("unsupported_state", (*path, "state"))
        if "current_position" not in attrs:
            return None
        position = attrs["current_position"]
        if type(position) is not int or not 0 <= position <= 100:
            raise HANormalizationError(
                "invalid_position", (*path, "attributes", "current_position")
            )
        return position
    if attrs.get("unit_of_measurement") != "°C":
        raise HANormalizationError("unsupported_unit", (*path, "attributes", "unit_of_measurement"))
    if _NUMBER.fullmatch(raw) is None:
        raise HANormalizationError("invalid_temperature", (*path, "state"))
    value = float(raw)
    if not math.isfinite(value) or value < -273.15:
        raise HANormalizationError("invalid_temperature", (*path, "state"))
    return value
