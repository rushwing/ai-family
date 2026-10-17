"""One acknowledged state_changed subscription per owned HA socket.

Payloads belong to a trusted adapter consumer, never to public diagnostics.
Delivery is serial and backpressured, with no replay or exactly-once claim.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import math
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import cast

from websockets.asyncio.client import ClientConnection

from .ha_configuration import HAConfiguration
from .ha_websocket import _MAX_MESSAGE, HAWebSocketClient, _constant, _object

__all__ = ["HAStateSubscriptionClient", "HASubscriptionHealth"]

_STATES = frozenset(("idle", "subscribing", "subscribed", "disconnected",
                     "reconnecting", "rejected", "failed", "closed"))
_REASONS = frozenset((None, "transport_failed", "timeout", "protocol_error",
                      "auth_failed", "reconnect_exhausted", "internal_error", "cancelled",
                      "subscription_rejected", "delivery_failed", "delivery_timeout"))


@dataclass(frozen=True, slots=True)
class HASubscriptionHealth:
    """Finite subscription status; transport connected is insufficient readiness."""

    state: str = "idle"
    reason: str | None = None
    sequence: int = 0

    def __post_init__(self) -> None:
        if (type(self.state) is not str or self.state not in _STATES
                or (self.reason is not None and type(self.reason) is not str)
                or self.reason not in _REASONS
                or type(self.sequence) is not int or self.sequence < 0):
            raise ValueError("invalid_subscription_health")

    @property
    def subscribed(self) -> bool:
        return self.state == "subscribed"

    def to_dict(self) -> dict[str, str | int | bool | None]:
        return {"state": self.state, "reason": self.reason,
                "sequence": self.sequence, "subscribed": self.subscribed}


def _float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("protocol_error")
    return number


def _decode(raw: str | bytes) -> dict[str, object]:
    if type(raw) is not str or len(raw.encode("utf-8")) > _MAX_MESSAGE:
        raise ValueError("protocol_error")
    value: object = json.loads(raw, object_pairs_hook=_object, parse_constant=_constant,
                               parse_float=_float)
    # A 64 KiB bound alone still permits thousands of nested tiny containers.
    # Limit accepted structure independently of Python's recursion settings.
    pending: list[tuple[object, int]] = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        if depth > 32:
            raise ValueError("protocol_error")
        if type(item) is dict:
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
    if (type(value) is not dict or type(value.get("id")) is not int
            or value["id"] != 1 or type(value.get("type")) is not str):
        raise ValueError("protocol_error")
    return cast(dict[str, object], value)


def _event(value: dict[str, object]) -> dict[str, object]:
    event = value.get("event")
    if (value["type"] != "event" or type(event) is not dict
            or event.get("event_type") != "state_changed"):
        raise ValueError("protocol_error")
    data = event.get("data")
    if (type(data) is not dict or type(data.get("entity_id")) is not str
            or not data["entity_id"] or "old_state" not in data or "new_state" not in data
            or (data["old_state"] is not None and type(data["old_state"]) is not dict)
            or (data["new_state"] is not None and type(data["new_state"]) is not dict)):
        raise ValueError("protocol_error")
    return cast(dict[str, object], event)


class HAStateSubscriptionClient(HAWebSocketClient):
    """Trusted async callback receives detached provider events, in wire order.

    Consumers must cooperate with cancellation and avoid blocking the event loop.
    Their payloads can contain private HA data; do not publish or log them.
    """

    __slots__ = ("_callback", "_delivery_timeout_ms", "_subscription")

    def __init__(self, configuration: HAConfiguration,
                 callback: Callable[[dict[str, object]], Awaitable[None]], *,
                 delivery_timeout_ms: int = 1000) -> None:
        if hasattr(self, "_configuration"):
            raise RuntimeError("client_initialized")
        if type(configuration) is not HAConfiguration:
            raise TypeError("invalid_configuration")
        if not callable(callback):
            raise TypeError("invalid_callback")
        if type(delivery_timeout_ms) is not int or not 1 <= delivery_timeout_ms <= 60000:
            raise ValueError("invalid_delivery_timeout")
        super().__init__(configuration)
        self._callback = callback
        self._delivery_timeout_ms = delivery_timeout_ms
        self._subscription = HASubscriptionHealth()

    def __repr__(self) -> str:
        return "HAStateSubscriptionClient(<redacted>)"

    def subscription_health(self) -> HASubscriptionHealth:
        return self._subscription

    async def aclose(self) -> None:
        # A consumer runs on the owned reader task. Joining that same task from
        # inside delivery would deadlock; its caller can schedule close instead.
        if asyncio.current_task() is self._worker:
            raise RuntimeError("close_from_consumer")
        await super().aclose()

    def _subscription_status(self, state: str, reason: str | None = None) -> None:
        old = self._subscription
        if old.state == "closed" or (old.state == state and old.reason == reason):
            return
        self._subscription = HASubscriptionHealth(state, reason, old.sequence + 1)

    def _publish(self, state: str, reason: str | None = None, *,
                 attempt: int | None = None) -> None:
        super()._publish(state, reason, attempt=attempt)
        if state == "closed":
            self._subscription_status("closed", self._subscription.reason)
        elif self._subscription.state not in ("closed", "rejected", "failed"):
            if state in ("disconnected", "reconnecting"):
                self._subscription_status(state, reason)
            elif state in ("failed", "auth_failed"):
                self._subscription_status("failed", reason)

    async def _consume_authenticated(self, socket: ClientConnection) -> str:
        self._subscription_status("subscribing")
        async with asyncio.timeout(self._configuration.request_timeout_ms / 1000):
            await socket.send('{"id":1,"type":"subscribe_events","event_type":"state_changed"}')
            result = _decode(await socket.recv())
            if result["type"] != "result" or type(result.get("success")) is not bool:
                raise ValueError("protocol_error")
            if result["success"] is False:
                self._subscription_status("rejected", "subscription_rejected")
                return "protocol_error"
            if "result" not in result or result["result"] is not None:
                raise ValueError("protocol_error")
        if self._closed:
            return "protocol_error"
        self._subscription_status("subscribed")
        while not self._closed:
            event = _event(_decode(await socket.recv()))
            if self._closed:
                break
            failure = await self._deliver(event)
            if failure is not None:
                self._subscription_status("failed", failure)
                return "protocol_error"
        return "protocol_error"

    async def _deliver(self, event: dict[str, object]) -> str | None:
        timer = asyncio.timeout(self._delivery_timeout_ms / 1000)
        try:
            async with timer:
                result = self._callback(event)
                if not inspect.isawaitable(result):
                    return "delivery_failed"
                await result
        except TimeoutError:
            return "delivery_timeout" if timer.expired() else "delivery_failed"
        except asyncio.CancelledError:
            current = asyncio.current_task()
            if current is not None and current.cancelling():
                raise
            return "delivery_failed"
        except Exception:
            return "delivery_failed"
        return "delivery_timeout" if timer.expired() else None
