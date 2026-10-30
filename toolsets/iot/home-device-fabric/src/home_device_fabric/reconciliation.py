"""REQ-036 single offline attempt. Capture, barriers, epochs and retries belong to owner.

Inputs are trusted detached adapter outputs, never query-caller provider payloads.
No network, clock, scheduler, persistence or implicit retry is performed here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import NoReturn, cast

from state_schema.canonical_state import DeviceState, Ordering, StateCollection, StateError
from state_schema.home_inventory import CANONICAL_ID_PATTERN, Inventory, InventoryError
from state_schema.provider_binding import BindingCollection, HAMapping

from .ha_discovery import HADiscoveryError, HADiscoverySnapshot
from .ha_mapping import HAMappingError, HAMappingResult
from .ha_normalization import HAEventNormalizer, HANormalizationError, _timestamp
from .state_store import CurrentStateStore, StateStoreError


class ReconciliationError(ValueError):
    """Fixed construction error, with no submitted data or exception chain."""

    def __init__(self) -> None:
        super().__init__("invalid_configuration")


class _Failure(Exception):
    def __init__(self, code: str, *, retryable: bool = False):
        self.code, self.retryable = code, retryable


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    outcome: str
    epoch: int | None
    failure_code: str | None
    buffered_event_count: int
    state_stale: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "outcome": self.outcome,
            "epoch": self.epoch,
            "failure_code": self.failure_code,
            "buffered_event_count": self.buffered_event_count,
            "state_stale": self.state_stale,
        }


def _positive(value: object) -> int:
    if type(value) is not int or value <= 0:
        raise _Failure("invalid_input")
    return value


def _object(value: object) -> dict[str, object]:
    if type(value) is not dict:
        raise _Failure("invalid_input")
    return cast(dict[str, object], value)


def _rebase(state: DeviceState, epoch: int, sequence: int) -> DeviceState:
    data = state.to_dict()
    reports = cast(dict[str, dict[str, object]], data["reported_state"])
    members = [*reports.values(), cast(dict[str, object], data["availability"])]
    for member in members:
        if member["observed_at"] is not None:
            member["ordering"] = {"epoch": epoch, "sequence": sequence}
    return DeviceState.from_dict(data)


class ReconnectReconciler:
    """Detached configuration; per-home serialization is an owner precondition."""

    __slots__ = (
        "_store",
        "_context",
        "_inventory",
        "_provider",
        "_profiles",
        "_capacity",
        "_bytes",
    )

    def __init__(
        self,
        *,
        store: CurrentStateStore,
        write_context: object,
        registered_inventory: object,
        provider_instance_id: object,
        profiles: object,
        max_buffer_events: object,
        max_input_bytes: object,
    ) -> None:
        valid = True
        try:
            inventory = Inventory.from_dict(registered_inventory)
            capacity, size = _positive(max_buffer_events), _positive(max_input_bytes)
            if (
                type(provider_instance_id) is not str
                or CANONICAL_ID_PATTERN.fullmatch(provider_instance_id) is None
                or type(profiles) is not list
            ):
                raise _Failure("invalid_input")
            seen: set[str] = set()
            for raw in profiles:
                profile = _object(raw)
                entity = profile.get("entity_id")
                if (
                    set(profile) != {"entity_id", "kind"}
                    or type(entity) is not str
                    or not entity
                    or entity.strip() != entity
                    or entity in seen
                    or profile["kind"] not in ("switch", "curtain", "temperature")
                ):
                    raise _Failure("invalid_input")
                seen.add(entity)
            home = inventory.home.id
            store._authorize(write_context, home, write=True)
            if store.inventory(write_context, home_id=home).to_dict() != inventory.to_dict():
                raise _Failure("invalid_input")
            context_json = json.dumps(write_context, allow_nan=False)
            profiles_json = json.dumps(profiles, allow_nan=False)
        except (ValueError, TypeError, _Failure, InventoryError):
            valid = False
        if not valid:
            raise ReconciliationError() from None
        self._store, self._context, self._inventory = store, context_json, inventory
        self._provider, self._profiles = provider_instance_id, profiles_json
        self._capacity, self._bytes = capacity, size

    def __repr__(self) -> str:
        return "ReconnectReconciler()"

    def __reduce__(self) -> NoReturn:
        raise TypeError("reconciler_serialization_forbidden")

    def reconcile(
        self,
        *,
        home_id: object,
        epoch: object,
        attempt_number: object,
        max_attempts: object,
        discovery_result: object,
        mapping_result: object,
        buffered_events: object,
        current_states: object,
        now_ms: object,
    ) -> ReconciliationResult:
        context = json.loads(self._context)
        count = 0
        generation: int | None = None
        # Admission never changes state, including invalid scope or attempt metadata.
        admitted = False
        try:
            self._store._authorize(context, home_id, write=True)
            if home_id != self._inventory.home.id:
                raise _Failure("invalid_input")
            generation = _positive(epoch)
            attempt, maximum = _positive(attempt_number), _positive(max_attempts)
            if attempt > maximum or type(now_ms) is not int or now_ms < 0:
                raise _Failure("invalid_input")
            admitted = True
            if type(buffered_events) is not list:
                raise _Failure("invalid_input")
            count = min(len(buffered_events), self._capacity)
            if len(buffered_events) > self._capacity:
                raise _Failure("buffer_overflow")
            if type(discovery_result) is HADiscoveryError:
                raise _Failure("discovery_failed", retryable=True)
            if type(discovery_result) is not HADiscoverySnapshot:
                raise _Failure("incomplete_snapshot", retryable=True)
            if type(mapping_result) is HAMappingError:
                raise _Failure("projection_failed")
            if (
                type(mapping_result) is not HAMappingResult
                or type(current_states) is not StateCollection
            ):
                raise _Failure("invalid_input")
            discovery = discovery_result.for_mapping()
            mapped = mapping_result.for_adapter()
            # JSON roundtrip detaches caller-owned envelopes; strict finite JSON only.
            serialized = json.dumps(
                [discovery, mapped, buffered_events, current_states.to_dict()],
                allow_nan=False,
                ensure_ascii=True,
            )
            if len(serialized.encode("utf-8")) > self._bytes:
                raise _Failure("invalid_input")
            captured = json.loads(serialized)[2]
            baseline, events = self._project(
                discovery, mapped, captured, current_states, generation
            )
            try:
                pinned = self._store.reconcile_home(
                    context,
                    home_id=home_id,
                    epoch=generation,
                    baseline_states={
                        "schema_version": 1,
                        "states": [s.to_dict() for s in baseline],
                    },
                    buffered_events=[s.to_dict() for s in events],
                    now_ms=now_ms,
                )
            except StateStoreError as error:
                raise _Failure(
                    "epoch_conflict" if error.code == "epoch_regression" else "store_failure",
                    retryable=error.code != "epoch_regression",
                ) from None
            except Exception:
                raise _Failure("store_failure", retryable=True) from None
            return ReconciliationResult("reconciled", pinned, None, len(events), False)
        except _Failure as error:
            code, retryable = error.code, error.retryable
        except (StateError, HANormalizationError, ValueError, TypeError, KeyError, OverflowError):
            code, retryable = "invalid_input", False
        except Exception:
            code, retryable = "projection_failed", False
        stale = False
        if admitted:
            try:
                self._store.mark_home_stale(context, home_id=home_id)
                stale = True
            except Exception:
                code, retryable = "stale_mark_failed", False
        outcome = "terminal_failure"
        if retryable:
            outcome = "exhausted_failure" if attempt == maximum else "retryable_failure"
        return ReconciliationResult(outcome, generation, code, count, stale)

    def _project(
        self,
        discovery: dict[str, list[dict[str, object]]],
        mapped: dict[str, object],
        captured: list[object],
        current: StateCollection,
        epoch: int,
    ) -> tuple[list[DeviceState], list[DeviceState]]:
        inventory = self._inventory.to_dict()
        previous = StateCollection.from_dict(current.to_dict(), inventory=inventory)
        old = {state.device_id: state for state in previous.states}
        expected = {device.id for device in self._inventory.devices}
        if set(old) != expected:
            raise _Failure("invalid_input")
        fresh = Inventory.from_dict(mapped["inventory"])
        if fresh.home.id != self._inventory.home.id or any(
            d.id not in expected for d in fresh.devices
        ):
            raise _Failure("mapping_mismatch")
        bindings = BindingCollection.from_dict(mapped["bindings"], inventory=inventory)
        selected: dict[str, str] = {}
        for binding in bindings.bindings:
            if binding.provider != "ha" or binding.provider_instance_id != self._provider:
                continue
            if not isinstance(binding.mapping, HAMapping) or len(binding.mapping.entity_ids) != 1:
                raise _Failure("projection_failed")
            if binding.device_id in selected.values():
                raise _Failure("projection_failed")
            selected[binding.mapping.entity_ids[0]] = binding.device_id
        profiles = [p for p in json.loads(self._profiles) if p["entity_id"] in selected]
        try:
            normalizer = HAEventNormalizer(
                inventory=inventory,
                bindings=mapped["bindings"],
                provider_instance_id=self._provider,
                profiles=profiles,
            )
        except HANormalizationError:
            raise _Failure("projection_failed") from None
        rows: dict[str, dict[str, object]] = {}
        times: dict[str, datetime] = {}
        for row in discovery["states"]:
            entity = row.get("entity_id")
            if type(entity) is not str or entity not in selected:
                continue
            if entity in rows:
                raise _Failure("projection_failed")
            rows[entity] = row
            try:
                times[entity] = datetime.fromisoformat(_timestamp(row.get("last_updated")))
            except HANormalizationError:
                raise _Failure("projection_failed") from None
        baseline: dict[str, DeviceState] = {}
        for device in expected:
            prior = _rebase(old[device], epoch, 0).to_dict()
            prior["desired_state"] = None
            prior["availability"] = {"status": "unknown", "observed_at": None, "ordering": None}
            if device not in selected.values():
                prior["reported_state"] = {}
            baseline[device] = DeviceState.from_dict(prior)
        for entity, row in rows.items():
            try:
                observation = normalizer.normalize(
                    {
                        "event_type": "state_changed",
                        "time_fired": row["last_updated"],
                        "data": {"entity_id": entity, "old_state": None, "new_state": row},
                    },
                    ordering={"epoch": epoch, "sequence": 0},
                )
            except HANormalizationError:
                raise _Failure("projection_failed") from None
            data = observation.to_dict()
            if observation.availability.status == "offline":
                data["reported_state"] = baseline[observation.device_id].to_dict()["reported_state"]
            baseline[observation.device_id] = DeviceState.from_dict(data)
        events: list[DeviceState] = []
        seen: set[str] = set()
        last_ordinal = 0
        for raw in captured:
            envelope = _object(raw)
            if set(envelope) != {
                "normalized_delta",
                "source_entity_id",
                "original_ordering",
                "observed_at",
                "capture_ordinal",
            }:
                raise _Failure("invalid_input")
            ordinal = _positive(envelope["capture_ordinal"])
            if ordinal <= last_ordinal:
                raise _Failure("invalid_input")
            last_ordinal = ordinal
            entity = envelope["source_entity_id"]
            if type(entity) is not str or not entity or entity.strip() != entity:
                raise _Failure("invalid_input")
            delta = DeviceState.from_dict(envelope["normalized_delta"])
            order = Ordering.from_dict(envelope["original_ordering"])
            observed = _timestamp(envelope["observed_at"])
            if (
                delta.home_id != self._inventory.home.id
                or delta.desired_state is not None
                or delta.availability.observed_at is None
                or _timestamp(delta.availability.observed_at) != observed
                or delta.availability.ordering != order
                or any(
                    report.ordering != order
                    or report.observed_at is None
                    or _timestamp(report.observed_at) != observed
                    for _, report in delta.reported_state
                )
            ):
                raise _Failure("invalid_input")
            identity = json.dumps([entity, delta.to_dict(), order.to_dict()], sort_keys=True)
            if identity in seen:
                continue
            seen.add(identity)
            if selected.get(entity) != delta.device_id:
                continue
            if entity in times and datetime.fromisoformat(observed) <= times[entity]:
                continue
            events.append(_rebase(delta, epoch, len(events) + 1))
        return [baseline[device] for device in sorted(expected)], events
