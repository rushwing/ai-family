"""Scoped rebuildable process-local canonical snapshots (REQ-029).

Contexts/grants are trusted composition inputs, not authentication tokens.
Full snapshot CAS is distinct from normalized-event application (REQ-030).
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Literal, NoReturn, cast

from state_schema.action_contracts import ActionError, RequesterContext
from state_schema.canonical_state import (
    DeviceState,
    Ordering,
    StateCollection,
    StateError,
    apply_state_update,
)
from state_schema.home_inventory import CANONICAL_ID_PATTERN, Inventory, InventoryError

Path = tuple[str | int, ...]
Freshness = Literal["uninitialized", "fresh", "stale"]


class StateStoreError(ValueError):
    """Fixed code/path, without submitted data or canonical error details."""

    def __init__(self, code: str, path: Path) -> None:
        self.code = code
        self.path = path
        super().__init__(code + ": " + ".".join(str(part) for part in path))


def _integer(value: object, field: str) -> int:
    if type(value) is not int or value < 0:
        raise StateStoreError("invalid_integer", (field,))
    return value


def _identifier(value: object) -> str:
    if type(value) is not str or CANONICAL_ID_PATTERN.fullmatch(value) is None:
        raise StateStoreError("invalid_identifier", ("device_id",))
    return value


def _context(value: object) -> RequesterContext:
    if type(value) is not dict:
        raise StateStoreError("invalid_context", ("context",))
    try:
        return RequesterContext.from_dict(value)
    except ActionError:
        raise StateStoreError("invalid_context", ("context",)) from None


def _key(context: RequesterContext) -> tuple[str, str, str, str]:
    return context.subject_id, context.family_member_id, context.home_id, context.role


@dataclass(frozen=True, slots=True)
class StateNotFound:
    home_id: str
    device_id: str

    def to_dict(self) -> dict[str, object]:
        return {"status": "not_found", "home_id": self.home_id, "device_id": self.device_id}


@dataclass(frozen=True, slots=True)
class StateView:
    state: DeviceState
    revision: int
    updated_at_ms: int | None
    freshness: Freshness

    def to_dict(self) -> dict[str, object]:
        return {
            "status": "found",
            "state": self.state.to_dict(),
            "revision": self.revision,
            "updated_at_ms": self.updated_at_ms,
            "freshness": self.freshness,
        }


@dataclass(frozen=True, slots=True)
class _Stored:
    state: DeviceState
    revision: int = 0
    updated_at_ms: int | None = None

    def view(self, now: int, max_age: int) -> StateView:
        updated = self.updated_at_ms
        if updated is not None and now < updated:
            raise StateStoreError("clock_regression", ("now_ms",))
        freshness: Freshness = (
            "uninitialized" if updated is None else "fresh" if now - updated <= max_age else "stale"
        )
        return StateView(self.state, self.revision, updated, freshness)


class CurrentStateStore:
    """Thread-safe in-memory snapshots; explicit grants on every operation."""

    __slots__ = ("_inventories", "_grants", "_rows", "_rebuilt", "_epochs", "_lock")

    def __init__(self, *, inventories: object, grants: object) -> None:
        if type(inventories) is not list or type(grants) is not list:
            raise StateStoreError("invalid_configuration", ("configuration",))
        homes: dict[str, Inventory] = {}
        rows: dict[tuple[str, str], _Stored] = {}
        for raw in inventories:
            try:
                inventory = Inventory.from_dict(raw)
            except InventoryError:
                raise StateStoreError("invalid_configuration", ("inventories",)) from None
            home = inventory.home.id
            if home in homes:
                raise StateStoreError("invalid_configuration", ("inventories",))
            homes[home] = inventory
            for device in inventory.devices:
                rows[home, device.id] = _Stored(
                    DeviceState.from_dict(
                        {
                            "home_id": home,
                            "device_id": device.id,
                            "desired_state": None,
                            "reported_state": {},
                            "availability": {
                                "status": "unknown",
                                "observed_at": None,
                                "ordering": None,
                            },
                        }
                    )
                )
        permissions: dict[tuple[str, str, str, str], str] = {}
        fields = {"subject_id", "family_member_id", "home_id", "role", "access"}
        for grant in grants:
            if type(grant) is not dict or set(grant) != fields:
                raise StateStoreError("invalid_configuration", ("grants",))
            data = cast(dict[str, object], grant)
            try:
                context = _context({k: v for k, v in data.items() if k != "access"})
            except StateStoreError:
                raise StateStoreError("invalid_configuration", ("grants",)) from None
            access = data["access"]
            key = _key(context)
            if (
                type(access) is not str
                or access not in ("read", "write")
                or context.home_id not in homes
                or key in permissions
                or (context.role == "kid" and access == "write")
            ):
                raise StateStoreError("invalid_configuration", ("grants",))
            permissions[key] = access
        self._inventories = homes
        self._rows = rows
        self._grants = permissions
        self._rebuilt: set[str] = set()
        self._epochs: dict[str, int] = {}
        self._lock = Lock()

    def __repr__(self) -> str:
        return "CurrentStateStore()"

    def __reduce__(self) -> NoReturn:
        raise TypeError("state_store_serialization_forbidden")

    def _authorize(self, context: object, home_id: object, *, write: bool) -> str:
        caller = _context(context)
        access = self._grants.get(_key(caller))
        if (
            type(home_id) is not str
            or home_id != caller.home_id
            or access is None
            or (write and access != "write")
        ):
            raise StateStoreError("forbidden", ("scope",))
        return home_id

    def read(
        self,
        context: object,
        *,
        home_id: object,
        device_id: object,
        now_ms: object,
        max_age_ms: object,
    ) -> StateView | StateNotFound:
        home = self._authorize(context, home_id, write=False)
        device = _identifier(device_id)
        now, age = _integer(now_ms, "now_ms"), _integer(max_age_ms, "max_age_ms")
        with self._lock:
            row = self._rows.get((home, device))
            if row is None:
                return StateNotFound(home, device)
            return row.view(now, age)

    def inventory(self, context: object, *, home_id: object) -> Inventory:
        """Authorized immutable canonical inventory; fixed for this store's lifetime."""
        home = self._authorize(context, home_id, write=False)
        return self._inventories[home]

    def snapshot(
        self, context: object, *, home_id: object, now_ms: object, max_age_ms: object,
    ) -> tuple[StateView, ...]:
        """Capture a whole home's views atomically against puts/rebuilds/events."""
        home = self._authorize(context, home_id, write=False)
        now, age = _integer(now_ms, "now_ms"), _integer(max_age_ms, "max_age_ms")
        with self._lock:
            return tuple(
                self._rows[home, device.id].view(now, age)
                for device in sorted(self._inventories[home].devices, key=lambda item: item.id)
            )

    def put(
        self,
        context: object,
        *,
        home_id: object,
        device_id: object,
        state: object,
        expected_revision: object,
        now_ms: object,
    ) -> StateView | StateNotFound:
        home = self._authorize(context, home_id, write=True)
        device = _identifier(device_id)
        expected = _integer(expected_revision, "expected_revision")
        now = _integer(now_ms, "now_ms")
        with self._lock:
            row = self._rows.get((home, device))
            if row is None:
                return StateNotFound(home, device)
            if row.revision != expected:
                raise StateStoreError("revision_conflict", ("expected_revision",))
            row.view(now, 0)  # Reject regressing elapsed time before publication.
            try:
                candidate = DeviceState.from_dict(state)
            except StateError:
                raise StateStoreError("invalid_state", ("state",)) from None
            if candidate.home_id != home or candidate.device_id != device:
                raise StateStoreError("identity_mismatch", ("state",))
            updated = _Stored(candidate, row.revision + 1, now)
            self._rows[home, device] = updated
            return updated.view(now, 0)

    def rebuild(
        self,
        context: object,
        *,
        home_id: object,
        states: object,
        now_ms: object,
    ) -> tuple[StateView, ...]:
        home = self._authorize(context, home_id, write=True)
        now = _integer(now_ms, "now_ms")
        try:
            collection = StateCollection.from_dict(
                states,
                inventory=self._inventories[home].to_dict(),
            )
        except StateError:
            raise StateStoreError("invalid_state", ("states",)) from None
        candidates = {state.device_id: state for state in collection.states}
        expected = {device.id for device in self._inventories[home].devices}
        if set(candidates) != expected:
            raise StateStoreError("incomplete_snapshot", ("states",))
        if any(state.desired_state is not None for state in candidates.values()):
            raise StateStoreError("unexpected_intent", ("states",))
        with self._lock:
            if home in self._rebuilt or any(
                self._rows[home, device].revision for device in expected
            ):
                raise StateStoreError("already_initialized", ("home_id",))
            updates = {
                (home, device.id): _Stored(candidates[device.id], 1, now)
                for device in self._inventories[home].devices
            }
            self._rows.update(updates)
            self._rebuilt.add(home)
            return tuple(row.view(now, 0) for row in updates.values())

    def advance_epoch(self, context: object, *, home_id: object, epoch: object) -> int:
        """Pin a caller-established home generation without refreshing snapshots."""
        home = self._authorize(context, home_id, write=True)
        generation = _integer(epoch, "epoch")
        with self._lock:
            # The bounded process-local store scans all rows and this home's
            # member orders under the publication lock. Computing the floor
            # from current snapshots also covers trusted put/rebuild changes.
            orders: list[Ordering | None] = []
            for (row_home, _), row in self._rows.items():
                if row_home != home:
                    continue
                orders.extend(report.ordering for _, report in row.state.reported_state)
                orders.append(row.state.availability.ordering)
                if row.state.desired_state is not None:
                    orders.append(row.state.desired_state.report_baseline)
            floor = max(
                (order.epoch for order in orders if order is not None),
                default=0,
            )
            if generation < max(floor, self._epochs.get(home, 0)):
                raise StateStoreError("epoch_regression", ("epoch",))
            self._epochs[home] = generation
            return generation

    def apply(
        self,
        context: object,
        *,
        home_id: object,
        device_id: object,
        event: object,
        now_ms: object,
    ) -> StateView | StateNotFound:
        """Merge caller-verified observations; canonical JSON cannot prove origin."""
        home = self._authorize(context, home_id, write=True)
        device = _identifier(device_id)
        now = _integer(now_ms, "now_ms")
        with self._lock:
            row = self._rows.get((home, device))
            if row is None:
                return StateNotFound(home, device)
            view = row.view(now, 0)
            epoch = self._epochs.get(home)
            if epoch is None:
                raise StateStoreError("epoch_uninitialized", ("epoch",))
            # Raise outside the parser handler so the canonical exception is not
            # retained as __context__, even though it contains submitted keys.
            candidate = None
            try:
                candidate = DeviceState.from_dict(event)
            except StateError:
                pass
            if candidate is None:
                raise StateStoreError("invalid_event", ("event",)) from None
            if candidate.home_id != home or candidate.device_id != device:
                raise StateStoreError("identity_mismatch", ("event",))
            if candidate.desired_state is not None:
                raise StateStoreError("unexpected_intent", ("event",))
            orders = [report.ordering for _, report in candidate.reported_state]
            orders.append(candidate.availability.ordering)
            if any(order is None for order in orders):
                raise StateStoreError("invalid_event", ("event",)) from None
            if any(order is not None and order.epoch != epoch for order in orders):
                raise StateStoreError("epoch_mismatch", ("event",))
            state = None
            try:
                merged = apply_state_update(
                    row.state.to_dict(),
                    current_epoch=epoch,
                    reported_state={
                        key: report.to_dict() for key, report in candidate.reported_state
                    },
                    availability=candidate.availability.to_dict(),
                )
                state = DeviceState.from_dict(merged)
            except StateError:
                pass
            if state is None:
                raise StateStoreError("invalid_event", ("event",)) from None
            if state == row.state:
                return view
            updated = _Stored(state, row.revision + 1, now)
            self._rows[home, device] = updated
            return updated.view(now, 0)
