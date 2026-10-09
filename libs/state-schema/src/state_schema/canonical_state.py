"""Strict offline canonical State and pure member ordering/convergence.

Factories validate external input; direct constructors are internal typed
records. Caller-established epochs fence generations. ACK is not State data.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, cast

from .home_inventory import (
    CANONICAL_ID_PATTERN,
    ErrorPath,
    Inventory,
    InventoryError,
    safe_inventory_path,
)

Scalar = bool | int | float | str
Convergence = Literal["not_requested", "unknown", "pending", "confirmed"]
_PROPERTY = re.compile(r"[a-z][a-z0-9_]{0,63}", re.ASCII)
_TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z", re.ASCII)


class StateError(ValueError):
    """Stable location and reason without submitted values or arbitrary keys."""

    def __init__(self, path: ErrorPath, message: str) -> None:
        self.path = path
        self.message = message
        location = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}" for part in path
        )
        super().__init__(f"{location}: {message}")


def _map(value: object, path: ErrorPath) -> dict[str, object]:
    if not isinstance(value, dict) or any(type(key) is not str for key in value):
        raise StateError(path, "expected an object with string field names")
    return cast(dict[str, object], value)


def _object(value: object, path: ErrorPath, fields: tuple[str, ...]) -> dict[str, object]:
    data = _map(value, path)
    for field in fields:
        if field not in data:
            raise StateError((*path, field), "required field is missing")
    if data.keys() - set(fields):
        raise StateError((*path, "<unknown>"), "unknown structural field")
    return data


def _integer(value: object, path: ErrorPath, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise StateError(
            path, "expected a positive integer" if minimum else "expected a nonnegative integer"
        )
    return value


def _identifier(value: object, path: ErrorPath) -> str:
    if type(value) is not str or CANONICAL_ID_PATTERN.fullmatch(value) is None:
        raise StateError(path, "expected a canonical identifier")
    return value


def _scalar(value: object, path: ErrorPath) -> Scalar:
    if type(value) not in (bool, int, float, str):
        raise StateError(path, "expected a boolean, finite number or string")
    if type(value) is float and not math.isfinite(value):
        raise StateError(path, "expected a finite number")
    return cast(Scalar, value)


def _timestamp(value: object, path: ErrorPath) -> str:
    if type(value) is not str or _TIME.fullmatch(value) is None:
        raise StateError(path, "expected a UTC timestamp ending in Z")
    # Enforce the contract independently of fromisoformat's version-dependent
    # acceptance/normalization (e.g. 24:00:00 in newer interpreters).
    hour, minute, second = (int(value[start : start + 2]) for start in (11, 14, 17))
    if hour > 23 or minute > 59 or second > 59:
        raise StateError(path, "invalid UTC clock time")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise StateError(path, "invalid UTC calendar timestamp") from None
    return value


def _properties(value: object, path: ErrorPath) -> dict[str, object]:
    data = _map(value, path)
    if any(_PROPERTY.fullmatch(key) is None for key in data):
        raise StateError((*path, "<property>"), "invalid canonical property name")
    return data


@dataclass(frozen=True, slots=True, order=True)
class Ordering:
    epoch: int
    sequence: int

    @classmethod
    def from_dict(cls, value: object, path: ErrorPath = ()) -> Ordering:
        data = _object(value, path, ("epoch", "sequence"))
        return cls(
            _integer(data["epoch"], (*path, "epoch")),
            _integer(data["sequence"], (*path, "sequence")),
        )

    def to_dict(self) -> dict[str, object]:
        return {"epoch": self.epoch, "sequence": self.sequence}


def _metadata(
    data: dict[str, object], path: ErrorPath, *, required: bool
) -> tuple[str | None, Ordering | None]:
    time, ordering = data["observed_at"], data["ordering"]
    if time is None and ordering is None and not required:
        return None, None
    return (
        _timestamp(time, (*path, "observed_at")),
        Ordering.from_dict(ordering, (*path, "ordering")),
    )


@dataclass(frozen=True, slots=True)
class Observation:
    status: Literal["known", "unknown"]
    value: Scalar | None
    observed_at: str | None
    ordering: Ordering | None

    @classmethod
    def from_dict(cls, value: object, path: ErrorPath = ()) -> Observation:
        data = _object(value, path, ("status", "value", "observed_at", "ordering"))
        status = data["status"]
        if type(status) is not str or status not in ("known", "unknown"):
            raise StateError((*path, "status"), "expected known or unknown")
        if status == "unknown":
            if data["value"] is not None:
                raise StateError((*path, "value"), "unknown observation requires null value")
            scalar = None
        else:
            scalar = _scalar(data["value"], (*path, "value"))
        time, ordering = _metadata(data, path, required=status == "known")
        return cls(cast(Literal["known", "unknown"], status), scalar, time, ordering)

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "value": self.value,
            "observed_at": self.observed_at,
            "ordering": None if self.ordering is None else self.ordering.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class Availability:
    status: Literal["online", "offline", "unknown"]
    observed_at: str | None
    ordering: Ordering | None

    @classmethod
    def from_dict(cls, value: object, path: ErrorPath = ()) -> Availability:
        data = _object(value, path, ("status", "observed_at", "ordering"))
        status = data["status"]
        if type(status) is not str or status not in ("online", "offline", "unknown"):
            raise StateError((*path, "status"), "expected online, offline or unknown")
        time, ordering = _metadata(data, path, required=status != "unknown")
        return cls(cast(Literal["online", "offline", "unknown"], status), time, ordering)

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "observed_at": self.observed_at,
            "ordering": None if self.ordering is None else self.ordering.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class DesiredState:
    revision: int
    values: tuple[tuple[str, Scalar], ...]
    report_baseline: Ordering | None

    @classmethod
    def from_dict(cls, value: object, path: ErrorPath = ()) -> DesiredState:
        data = _object(value, path, ("revision", "values", "report_baseline"))
        revision = _integer(data["revision"], (*path, "revision"), 1)
        properties = _properties(data["values"], (*path, "values"))
        if not properties:
            raise StateError((*path, "values"), "desired values must not be empty")
        values = tuple(
            (key, _scalar(raw, (*path, "values", key))) for key, raw in properties.items()
        )
        baseline = data["report_baseline"]
        return cls(
            revision,
            values,
            None if baseline is None else Ordering.from_dict(baseline, (*path, "report_baseline")),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "revision": self.revision,
            "values": dict(self.values),
            "report_baseline": None
            if self.report_baseline is None
            else self.report_baseline.to_dict(),
        }


def _reports(value: object, path: ErrorPath) -> tuple[tuple[str, Observation], ...]:
    return tuple(
        (key, Observation.from_dict(raw, (*path, key)))
        for key, raw in _properties(value, path).items()
    )


@dataclass(frozen=True, slots=True)
class DeviceState:
    home_id: str
    device_id: str
    desired_state: DesiredState | None
    reported_state: tuple[tuple[str, Observation], ...]
    availability: Availability

    @classmethod
    def from_dict(cls, value: object, path: ErrorPath = ()) -> DeviceState:
        """Validate shape only; collection validation also checks inventory."""
        data = _object(
            value, path, ("home_id", "device_id", "desired_state", "reported_state", "availability")
        )
        home = _identifier(data["home_id"], (*path, "home_id"))
        device = _identifier(data["device_id"], (*path, "device_id"))
        desired = data["desired_state"]
        intent = (
            None if desired is None else DesiredState.from_dict(desired, (*path, "desired_state"))
        )
        reports = _reports(data["reported_state"], (*path, "reported_state"))
        availability = Availability.from_dict(data["availability"], (*path, "availability"))
        return cls(home, device, intent, reports, availability)

    def to_dict(self) -> dict[str, object]:
        return {
            "home_id": self.home_id,
            "device_id": self.device_id,
            "desired_state": None if self.desired_state is None else self.desired_state.to_dict(),
            "reported_state": {key: report.to_dict() for key, report in self.reported_state},
            "availability": self.availability.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class StateCollection:
    schema_version: Literal[1]
    states: tuple[DeviceState, ...]

    @classmethod
    def from_dict(cls, value: object, *, inventory: object) -> StateCollection:
        data = _object(value, (), ("schema_version", "states"))
        if type(data["schema_version"]) is not int or data["schema_version"] != 1:
            raise StateError(("schema_version",), "expected supported integer schema version 1")
        raw = data["states"]
        if not isinstance(raw, list):
            raise StateError(("states",), "expected a list")
        try:
            canonical = Inventory.from_dict(inventory)
        except InventoryError as error:
            raise StateError(
                ("inventory", *safe_inventory_path(error.path)), "invalid canonical inventory"
            ) from None
        states = tuple(
            DeviceState.from_dict(item, ("states", index)) for index, item in enumerate(raw)
        )
        devices = {device.id for device in canonical.devices}
        seen: set[str] = set()
        for index, state in enumerate(states):
            path: ErrorPath = ("states", index)
            if state.home_id != canonical.home.id:
                raise StateError((*path, "home_id"), "must reference this inventory Home")
            if state.device_id not in devices:
                raise StateError((*path, "device_id"), "unknown Device in this inventory Home")
            if state.device_id in seen:
                raise StateError((*path, "device_id"), "duplicate canonical Device state")
            seen.add(state.device_id)
        return cls(1, states)

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": self.schema_version, "states": [s.to_dict() for s in self.states]}


def validate_state(data: object) -> dict[str, object]:
    return DeviceState.from_dict(data).to_dict()


def validate_states(data: object, *, inventory: object) -> dict[str, object]:
    return StateCollection.from_dict(data, inventory=inventory).to_dict()


def _epoch(state: DeviceState, value: object) -> int:
    epoch = _integer(value, ("current_epoch",))
    orders = [report.ordering for _, report in state.reported_state]
    orders.append(state.availability.ordering)
    if state.desired_state is not None:
        orders.append(state.desired_state.report_baseline)
    if any(order is not None and order.epoch > epoch for order in orders):
        raise StateError(("current_epoch",), "cannot lower the accepted generation")
    return epoch


def _identical(left: object, right: object) -> bool:
    """Exact typed replay, including int/float distinctions and map order independence."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(_identical(left[k], right[k]) for k in left)
    return bool(left == right)


def _update_member(
    accepted: Observation | Availability | None,
    candidate: Observation | Availability,
    epoch: int,
    path: ErrorPath,
) -> Observation | Availability:
    order = candidate.ordering
    if order is None:
        raise StateError((*path, "ordering"), "update event requires ordering")
    if order.epoch != epoch:
        raise StateError(
            (*path, "ordering", "epoch"), "update must belong to the current generation"
        )
    if accepted is None or accepted.ordering is None or order > accepted.ordering:
        return candidate
    if order < accepted.ordering:
        return accepted
    if not _identical(accepted.to_dict(), candidate.to_dict()):
        raise StateError((*path, "ordering"), "conflicting replay at the same ordering")
    return accepted


def apply_state_update(
    data: object,
    *,
    current_epoch: object,
    reported_state: object = None,
    availability: object = None,
    desired_state: object = None,
) -> dict[str, object]:
    """Apply detached partial events; None means no update, never implicit clearing."""
    accepted = DeviceState.from_dict(data)
    epoch = _epoch(accepted, current_epoch)
    reports = dict(accepted.reported_state)
    # Parse entire candidate shapes first; all results stay local until return.
    candidates = () if reported_state is None else _reports(reported_state, ("reported_state",))
    available = (
        None if availability is None else Availability.from_dict(availability, ("availability",))
    )
    desired = (
        None if desired_state is None else DesiredState.from_dict(desired_state, ("desired_state",))
    )
    for key, candidate in candidates:
        reports[key] = cast(
            Observation, _update_member(reports.get(key), candidate, epoch, ("reported_state", key))
        )
    final_availability = accepted.availability
    if available is not None:
        final_availability = cast(
            Availability, _update_member(final_availability, available, epoch, ("availability",))
        )
    final_desired = accepted.desired_state
    if desired is not None:
        baseline = desired.report_baseline
        if baseline is not None and baseline.epoch > epoch:
            raise StateError(
                ("desired_state", "report_baseline", "epoch"),
                "intent baseline cannot belong to a future generation",
            )
        if final_desired is None or desired.revision > final_desired.revision:
            final_desired = desired
        elif desired.revision == final_desired.revision:
            if not _identical(desired.to_dict(), final_desired.to_dict()):
                raise StateError(
                    ("desired_state", "revision"), "conflicting replay at the same revision"
                )
    return DeviceState(
        accepted.home_id,
        accepted.device_id,
        final_desired,
        tuple(reports.items()),
        final_availability,
    ).to_dict()


def _matches(left: Scalar, right: Scalar) -> bool:
    if type(left) in (int, float) and type(right) in (int, float):
        return left == right
    return type(left) is type(right) and left == right


def evaluate_convergence(data: object, *, current_epoch: object) -> Convergence:
    """Derive post-baseline observed agreement; ACK and ambient clocks have no role."""
    state = DeviceState.from_dict(data)
    epoch = _epoch(state, current_epoch)
    desired = state.desired_state
    if desired is None:
        return "not_requested"
    baseline = desired.report_baseline
    available = state.availability
    if (
        baseline is None
        or baseline.epoch != epoch
        or available.status != "online"
        or available.ordering is None
        or available.ordering.epoch != epoch
    ):
        return "unknown"
    reports = dict(state.reported_state)
    matches = True
    for key, target in desired.values:
        report = reports.get(key)
        if (
            report is None
            or report.status != "known"
            or report.ordering is None
            or report.ordering.epoch != epoch
            or report.ordering <= baseline
        ):
            return "unknown"
        matches = matches and _matches(target, cast(Scalar, report.value))
    return "confirmed" if matches else "pending"
