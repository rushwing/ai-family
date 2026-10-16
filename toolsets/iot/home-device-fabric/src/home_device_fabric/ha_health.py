"""Adapter-owned, finite REST/socket health. No device availability claims."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import NoReturn

from .ha_configuration import HAConfiguration
from .ha_rest import HARestClient, HARestError
from .ha_websocket import HAConnectionHealth, HAWebSocketClient

__all__ = ["HAHealthMonitor", "HAIntegrationHealth"]

_REST_STATES = frozenset(("unknown", "reachable", "unreachable", "auth_failed"))
_REASONS = frozenset((None, "auth_failed", "timeout", "transport_failed", "http_error",
                      "invalid_response", "client_closed", "client_busy",
                      "invalid_correlation_id", "stale", "internal_error"))


@dataclass(frozen=True, slots=True)
class HAIntegrationHealth:
    """Detached observations; closed retains component diagnostics, not readiness."""

    rest_state: str = "unknown"
    rest_reason: str | None = None
    websocket: HAConnectionHealth = HAConnectionHealth()
    closed: bool = False
    sequence: int = 0

    def __post_init__(self) -> None:
        if (type(self.rest_state) is not str or self.rest_state not in _REST_STATES
                or (self.rest_reason is not None and type(self.rest_reason) is not str)
                or self.rest_reason not in _REASONS
                or type(self.websocket) is not HAConnectionHealth
                or type(self.closed) is not bool
                or type(self.sequence) is not int or self.sequence < 0
                or (self.rest_state == "reachable" and self.rest_reason is not None)
                or (self.rest_state == "auth_failed" and self.rest_reason != "auth_failed")
                or (self.rest_reason == "auth_failed" and self.rest_state != "auth_failed")):
            raise ValueError("invalid_integration_health")

    @property
    def state(self) -> str:
        if self.closed:
            return "closed"
        if self.rest_state == "auth_failed" or self.websocket.state == "auth_failed":
            return "auth_failed"
        if self.websocket.state == "reconnecting":
            return "reconnecting"
        if self.rest_state == "reachable" and self.websocket.state == "connected":
            return "connected"
        return "disconnected"

    @property
    def rest_reachable(self) -> bool | None:
        if self.closed or self.rest_state == "unknown":
            return None
        return self.rest_state == "reachable"

    @property
    def event_stream_connected(self) -> bool:
        return not self.closed and self.websocket.state == "connected"

    def to_dict(self) -> dict[str, object]:
        return {"state": self.state, "rest_state": self.rest_state,
                "rest_reachable": self.rest_reachable, "rest_reason": self.rest_reason,
                "event_stream_connected": self.event_stream_connected,
                "websocket": self.websocket.to_dict(), "closed": self.closed,
                "sequence": self.sequence}


def _clock() -> float:
    return asyncio.get_running_loop().time()


async def _sleep(seconds: float) -> None:
    await asyncio.sleep(seconds)


async def _drain(task: asyncio.Task[None]) -> None:
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            pass
    if not task.cancelled():
        task.result()


class HAHealthMonitor:
    """Single-use composition of the accepted REST and WebSocket clients."""

    __slots__ = ("_rest", "_socket", "_interval", "_correlation", "_health",
                 "_rest_state", "_rest_reason", "_last_success", "_loop", "_started",
                 "_closed", "_worker", "_closer", "_clients_closing")

    def __init__(self, configuration: HAConfiguration, *,
                 observation_interval_ms: int = 1000) -> None:
        if hasattr(self, "_rest"):
            raise RuntimeError("client_initialized")
        if type(configuration) is not HAConfiguration:
            raise TypeError("invalid_configuration")
        if type(observation_interval_ms) is not int or not 1 <= observation_interval_ms <= 60000:
            raise ValueError("invalid_observation_interval")
        self._interval = observation_interval_ms / 1000
        # These single-character IDs cannot contain any other nonempty token.
        self._correlation = "1" if configuration.access_token_for_transport() == "0" else "0"
        self._rest = HARestClient(configuration)
        self._socket = HAWebSocketClient(configuration)
        self._health = HAIntegrationHealth()
        self._rest_state = "unknown"
        self._rest_reason: str | None = None
        self._last_success: float | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._started = False
        self._closed = False
        self._clients_closing = False
        self._worker: asyncio.Task[None] | None = None
        self._closer: asyncio.Task[None] | None = None

    def __repr__(self) -> str:
        return "HAHealthMonitor(<redacted>)"

    def __reduce__(self) -> NoReturn:
        raise TypeError("client_serialization_refused")

    def __getstate__(self) -> NoReturn:
        raise TypeError("client_serialization_refused")

    def _bind(self) -> None:
        loop = asyncio.get_running_loop()
        if self._loop is not None and self._loop is not loop:
            raise RuntimeError("wrong_event_loop")
        self._loop = loop

    def health(self) -> HAIntegrationHealth:
        if self._started and not self._closed:
            # A synchronous observation must never return expired success even
            # if the sampler was delayed. Read only on the owning event loop.
            if asyncio.get_running_loop() is not self._loop:
                raise RuntimeError("wrong_event_loop")
            self._sample()
        return self._health

    def _publish(self, *, closed: bool = False) -> None:
        if self._closed and not closed:
            return
        candidate = HAIntegrationHealth(self._rest_state, self._rest_reason,
                                        self._socket.health(), closed, self._health.sequence)
        if candidate != self._health:
            self._health = HAIntegrationHealth(
                candidate.rest_state, candidate.rest_reason, candidate.websocket,
                candidate.closed, candidate.sequence + 1)

    def _sample(self) -> None:
        if self._closed:
            return
        if (self._rest_state == "reachable" and self._last_success is not None
                and _clock() >= self._last_success + self._interval):
            self._rest_state, self._rest_reason = "unknown", "stale"
        self._publish()

    def _mark_closed(self) -> None:
        if not self._closed:
            self._closed = True
            self._publish(closed=True)

    def _begin_close(self) -> asyncio.Task[None]:
        if self._closer is None:
            self._mark_closed()
            if self._worker is not None and not self._worker.done():
                self._worker.cancel()
            self._closer = asyncio.create_task(self._finish_close(), name="ha-health-close")
        return self._closer

    async def run(self) -> None:
        self._bind()
        if self._closed:
            raise RuntimeError("client_closed")
        if self._started:
            raise RuntimeError("client_started")
        self._started = True
        worker = asyncio.create_task(self._run(), name="ha-health-monitor")
        self._worker = worker
        try:
            await asyncio.shield(worker)
        except asyncio.CancelledError:
            await _drain(self._begin_close())
            current = asyncio.current_task()
            if current is not None and current.cancelling():
                raise

    async def aclose(self) -> None:
        self._bind()
        await asyncio.shield(self._begin_close())

    async def _finish_close(self) -> None:
        try:
            if self._worker is not None:
                await _drain(self._worker)
        except BaseException:
            # run owns worker failures. Child cleanup is owned by _run/finally.
            pass
        finally:
            # A task cancelled before its first instruction never enters finally.
            await self._close_clients()

    async def _close_clients(self) -> None:
        if self._clients_closing:
            return
        self._clients_closing = True
        await asyncio.gather(self._rest.aclose(), self._socket.aclose(), return_exceptions=True)

    async def _finish_workers(self, tasks: list[asyncio.Task[None]]) -> None:
        for task in tasks:
            if not task.done() and not task.cancelling():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await self._close_clients()

    async def _run(self) -> None:
        tasks = [asyncio.create_task(self._socket.run(), name="ha-health-websocket"),
                 asyncio.create_task(self._probe(), name="ha-health-rest"),
                 asyncio.create_task(self._observe(), name="ha-health-observe")]
        failed = False
        try:
            await asyncio.gather(*tasks)
        except Exception:
            failed = True
        finally:
            self._mark_closed()
            cleanup = asyncio.create_task(self._finish_workers(tasks), name="ha-health-cleanup")
            await _drain(cleanup)
        if failed:
            # Construct outside the handler so no raw worker context is retained.
            raise RuntimeError("health_monitor_failed")

    async def _probe(self) -> None:
        while not self._closed:
            started = _clock()
            state, reason = "reachable", None
            try:
                await self._rest.runtime_info(correlation_id=self._correlation)
            except HARestError as error:
                state = "auth_failed" if error.code == "auth_failed" else "unreachable"
                reason = error.code
            except Exception:
                state, reason = "unreachable", "internal_error"
            if self._closed:
                return
            self._rest_state, self._rest_reason = state, reason
            self._last_success = _clock() if state == "reachable" else None
            self._sample()
            await _sleep(max(0, started + self._interval - _clock()))

    async def _observe(self) -> None:
        while not self._closed:
            self._sample()
            await _sleep(self._interval)
