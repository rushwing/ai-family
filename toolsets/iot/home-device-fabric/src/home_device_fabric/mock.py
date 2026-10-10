"""Synchronous virtual-time simulator; callers own State/Task adjudication."""

from __future__ import annotations

import heapq
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol, cast, runtime_checkable

from state_schema.action_contracts import ActionError, Task, validate_result, validate_task
from state_schema.canonical_state import DeviceState, StateError, apply_state_update
from state_schema.provider_binding import BindingError, ProviderBinding
from state_schema.provider_contracts import (
    DeviceRegistration,
    MockConfiguration,
    NormalizedInput,
    ProviderError,
    ProviderOutcome,
    integer,
    json_snapshot,
    token,
)


@dataclass(frozen=True, slots=True)
class Delivery:
    time_ms: int
    input: NormalizedInput | None
    outcome: ProviderOutcome | None

    def to_dict(self) -> dict[str, object]:
        return {
            "time_ms": self.time_ms,
            "input": None if self.input is None else self.input.to_dict(),
            "outcome": None if self.outcome is None else self.outcome.to_dict(),
        }


@runtime_checkable
class ProviderProtocol(Protocol):
    def discover(self) -> tuple[DeviceRegistration, ...]: ...
    def snapshot(self) -> tuple[DeviceState, ...]: ...
    def submit(self, task: object, *, binding: object, attempt_id: object) -> None: ...
    def advance(self, now_ms: object) -> Iterator[Delivery]: ...
    def settle(self, task: object) -> None: ...

    @property
    def now_ms(self) -> int: ...
    @property
    def dispatch_log(self) -> tuple[dict[str, object], ...]: ...
    @property
    def delivery_log(self) -> tuple[dict[str, object], ...]: ...


@dataclass
class _Attempt:
    task: Task
    deadline: int
    state: str = "running"
    settled: Task | None = None


class MockProvider:
    """No wall clock, random data, ambient config, network or shared-store writes."""

    def __init__(self, configuration: object) -> None:
        self._config = MockConfiguration.from_dict(configuration)
        self._now = 0
        self._advancing = False
        self._serial = 0
        self._queue: list[tuple[int, int, str, NormalizedInput | None, ProviderOutcome | None]] = []
        self._attempts: dict[str, _Attempt] = {}
        self._dispatch: list[dict[str, object]] = []
        self._deliveries: list[Delivery] = []
        self._snapshots = {
            r.device_id: DeviceState.from_dict(
                {
                    "home_id": r.home_id,
                    "device_id": r.device_id,
                    "desired_state": None,
                    "reported_state": {},
                    "availability": {"status": "unknown", "observed_at": None, "ordering": None},
                }
            )
            for r in self._config.devices
        }

    @property
    def now_ms(self) -> int:
        return self._now

    @property
    def dispatch_log(self) -> tuple[dict[str, object], ...]:
        return tuple(cast(dict[str, object], json_snapshot(item)) for item in self._dispatch)

    @property
    def delivery_log(self) -> tuple[dict[str, object], ...]:
        return tuple(item.to_dict() for item in self._deliveries)

    def discover(self) -> tuple[DeviceRegistration, ...]:
        return self._config.devices

    def snapshot(self) -> tuple[DeviceState, ...]:
        return tuple(self._snapshots.values())

    def submit(self, task: object, *, binding: object, attempt_id: object) -> None:
        if self._advancing:
            raise ProviderError("advance_in_progress")
        clean = json_snapshot(task)
        try:
            parsed = Task.from_dict(
                validate_task(
                    clean,
                    inventory=self._config.inventory.to_dict(),
                    catalogue=self._config.catalogue.to_dict(),
                )
            )
        except ActionError:
            raise ProviderError("invalid_task") from None
        if parsed.state != "running":
            raise ProviderError("invalid_task")
        identity = parsed.request.identity
        reg = self._config.registration(identity.home_id, identity.device_id)
        if (identity.capability_id, identity.capability_version) not in reg.supported_capabilities:
            raise ProviderError("unsupported")
        try:
            selected = ProviderBinding.from_dict(json_snapshot(binding))
        except BindingError:
            raise ProviderError("binding_mismatch") from None
        if selected != reg.binding:
            raise ProviderError("binding_mismatch")
        attempt = token(attempt_id, "invalid_attempt")
        script = next(
            (
                s
                for s in self._config.scenarios
                if (s.task_id, s.attempt_id) == (parsed.task_id, attempt)
            ),
            None,
        )
        if script is None or parsed.task_id in self._attempts:
            raise ProviderError("invalid_attempt")
        # Validate every item before allocating a deadline, queue entry or log.
        for item in script.deliveries:
            if item.outcome is not None:
                try:
                    validate_result(
                        item.outcome.result.to_dict(),
                        task=parsed.to_dict(),
                        inventory=self._config.inventory.to_dict(),
                        catalogue=self._config.catalogue.to_dict(),
                    )
                except ActionError:
                    raise ProviderError("invalid_outcome") from None
            if item.input is not None:
                inp = item.input.to_dict()
                corr = inp["correlation"]
                if corr is not None:
                    if (
                        corr != {"task_id": parsed.task_id, "trace_id": parsed.trace_id}
                        or inp["home_id"] != identity.home_id
                        or inp["device_id"] != identity.device_id
                        or (
                            inp["kind"] != "availability"
                            and (inp["capability_id"], inp["capability_version"])
                            != (identity.capability_id, identity.capability_version)
                        )
                    ):
                        raise ProviderError("invalid_input")
        desc = self._config.catalogue.get(identity.capability_id, identity.capability_version)
        timeout = dict(desc.actions)[identity.action_id].timeout_ms
        self._attempts[parsed.task_id] = _Attempt(parsed, self._now + timeout)
        self._dispatch.append(
            {
                "time_ms": self._now,
                "task_id": parsed.task_id,
                "trace_id": parsed.trace_id,
                "attempt_id": attempt,
                "binding": selected.to_dict(),
            }
        )
        for item in script.deliveries:
            heapq.heappush(
                self._queue,
                (self._now + item.delay_ms, self._serial, parsed.task_id, item.input, item.outcome),
            )
            self._serial += 1

    def settle(self, task: object) -> None:
        try:
            parsed = Task.from_dict(
                validate_task(
                    json_snapshot(task),
                    inventory=self._config.inventory.to_dict(),
                    catalogue=self._config.catalogue.to_dict(),
                )
            )
        except (ActionError, ProviderError):
            raise ProviderError("invalid_settlement") from None
        attempt = self._attempts.get(parsed.task_id)
        if attempt is None or parsed.state in ("accepted", "running"):
            raise ProviderError("invalid_settlement")
        original = attempt.task
        if (
            parsed.request != original.request
            or parsed.requester != original.requester
            or parsed.dispatch_context != original.dispatch_context
            or parsed.completion_policy != original.completion_policy
            or parsed.trace_id != original.trace_id
        ):
            raise ProviderError("invalid_settlement")
        if attempt.state != "running":
            # A generated timeout cannot be replaced by subsequent success/cancel.
            if attempt.state != parsed.state or (
                attempt.settled is not None and parsed != attempt.settled
            ):
                raise ProviderError("invalid_settlement")
        attempt.state = parsed.state
        attempt.settled = parsed

    def _observe(self, item: NormalizedInput, attempt: _Attempt) -> None:
        inp = item.to_dict()
        if inp["kind"] == "event":
            return
        device = cast(str, inp["device_id"])
        current = self._snapshots[device]
        dispatch = attempt.task.dispatch_context
        epoch = 1 if inp["correlation"] is None or dispatch is None else dispatch.current_epoch
        try:
            state = apply_state_update(
                current.to_dict(),
                current_epoch=epoch,
                reported_state={cast(str, inp["member"]): inp["payload"]}
                if inp["kind"] == "property"
                else None,
                availability=inp["payload"] if inp["kind"] == "availability" else None,
            )
        except StateError:
            # Valid adversarial provenance is delivered for caller assertions,
            # but conflicting/wrong-generation reports never replace snapshots.
            return
        self._snapshots[device] = DeviceState.from_dict(state)

    def _timeout(self, attempt: _Attempt) -> ProviderOutcome:
        task = attempt.task
        result = {
            "schema_version": 1,
            "task_id": task.task_id,
            "trace_id": task.trace_id,
            **task.request.identity.to_dict(),
            "state": "timed_out",
            "output": {"present": False, "value": None},
            "error": {"code": "provider_timeout"},
            "evidence": None,
            "physical_outcome": "unverified",
        }
        return ProviderOutcome.from_dict(
            {
                "schema_version": 1,
                "provider": "mock",
                "provider_instance_id": self._config.provider_instance_id,
                "result": result,
            }
        )

    def advance(self, now_ms: object) -> Iterator[Delivery]:
        if self._advancing:
            raise ProviderError("advance_in_progress")
        target = integer(now_ms, "invalid_time")
        if target < self._now:
            raise ProviderError("invalid_time")
        self._advancing = True
        try:
            while True:
                due = [
                    (a.deadline, n)
                    for n, a in self._attempts.items()
                    if a.state == "running" and a.deadline <= target
                ]
                deadline = min(due) if due else None
                queued_time = (
                    self._queue[0][0] if self._queue and self._queue[0][0] <= target else None
                )
                if deadline is not None and (queued_time is None or deadline[0] <= queued_time):
                    time_ms, task_id = deadline
                    attempt = self._attempts[task_id]
                    attempt.state = "timed_out"
                    timeout_out = self._timeout(attempt)
                    item = Delivery(time_ms, None, timeout_out)
                elif queued_time is not None:
                    time_ms, _, task_id, inp, out = heapq.heappop(self._queue)
                    attempt = self._attempts[task_id]
                    if out is not None and attempt.state != "running":
                        continue
                    if (
                        inp is not None
                        and attempt.state == "cancelled"
                        and inp.to_dict()["correlation"] is not None
                    ):
                        continue
                    if inp is not None:
                        self._observe(inp, attempt)
                    item = Delivery(time_ms, inp, out)
                else:
                    break
                self._now = time_ms
                self._deliveries.append(item)
                yield item
            self._now = target
        finally:
            self._advancing = False
