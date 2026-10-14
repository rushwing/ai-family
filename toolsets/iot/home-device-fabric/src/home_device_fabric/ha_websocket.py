"""Single-use HA connection lifecycle. No subscriptions or device commands.

Public diagnostics contain finite constants only. Wire logs, raw serialization
and ambient proxy/trust overrides are excluded; private process introspection
is outside this boundary. The retry budget covers the entire client lifetime.
"""

from __future__ import annotations

import asyncio
import json
import logging
import ssl
from dataclasses import dataclass
from typing import NoReturn

from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import (
    ConnectionClosed,
    InvalidHandshake,
    InvalidStatus,
)

from .ha_configuration import HAConfiguration

__all__ = ["HAWebSocketClient", "HAConnectionHealth"]

_STATES = frozenset(("disconnected", "connecting", "authenticating", "connected",
                     "reconnecting", "auth_failed", "failed", "closed"))
_REASONS = frozenset((None, "transport_failed", "timeout", "protocol_error",
                      "auth_failed", "reconnect_exhausted", "internal_error", "cancelled"))
_MAX_MESSAGE = 65536
_CLEANUP_SECONDS = 1.0

# An unregistered, disabled logger doesn't propagate to application/root DEBUG
# handlers. websockets otherwise logs the credential-bearing auth frame.
_WIRE_LOGGER = logging.Logger("home_device_fabric.private_socket")
_WIRE_LOGGER.disabled = True
_WIRE_LOGGER.propagate = False


@dataclass(frozen=True, slots=True)
class HAConnectionHealth:
    """Immutable current lifecycle snapshot; never a device availability claim."""

    state: str = "disconnected"
    reason: str | None = None
    reconnect_attempt: int = 0
    sequence: int = 0

    def __post_init__(self) -> None:
        if (type(self.state) is not str or self.state not in _STATES
                or (self.reason is not None and type(self.reason) is not str)
                or self.reason not in _REASONS
                or type(self.reconnect_attempt) is not int
                or not 0 <= self.reconnect_attempt <= 32
                or type(self.sequence) is not int or self.sequence < 0):
            raise ValueError("invalid_health")

    def to_dict(self) -> dict[str, str | int | None]:
        return {"state": self.state, "reason": self.reason,
                "reconnect_attempt": self.reconnect_attempt, "sequence": self.sequence}


class _NoRedirectConnect(connect):
    def process_redirect(self, exc: Exception) -> Exception:
        return exc


def _tls_context() -> ssl.SSLContext:
    # Use compiled OpenSSL root paths, not environment-selected cafile/capath.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    if hasattr(ssl, "enum_certificates"):
        # Windows trust stores are loaded explicitly without set_default_verify_paths
        # (which also honors SSL_CERT_FILE/SSL_CERT_DIR).
        for store in ("CA", "ROOT"):
            for certificate, encoding, trust in ssl.enum_certificates(store):
                if encoding == "x509_asn" and (
                    trust is True or (isinstance(trust, set)
                                      and ssl.Purpose.SERVER_AUTH.oid in trust)
                ):
                    context.load_verify_locations(cadata=certificate)
    else:
        defaults = ssl.get_default_verify_paths()
        context.load_verify_locations(cafile=defaults.openssl_cafile,
                                     capath=defaults.openssl_capath)
    return context


async def _connect(configuration: HAConfiguration) -> ClientConnection:
    root = configuration.base_url
    secure = root.startswith("https:")
    uri = ("wss:" if secure else "ws:") + root.split(":", 1)[1] + "/api/websocket"
    return await _NoRedirectConnect(
        uri, proxy=None, compression=None, additional_headers=None,
        user_agent_header=None, open_timeout=configuration.request_timeout_ms / 1000,
        ping_interval=20, ping_timeout=20, close_timeout=1,
        max_size=_MAX_MESSAGE, max_queue=4, logger=_WIRE_LOGGER,
        ssl=_tls_context() if secure else None,
    )


async def _sleep(seconds: float) -> None:
    await asyncio.sleep(seconds)


def _clock() -> float:
    return asyncio.get_running_loop().time()


def _object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("protocol_error")
        result[key] = value
    return result


def _constant(value: str) -> NoReturn:
    raise ValueError("protocol_error")


def _message_type(raw: str | bytes) -> str:
    if type(raw) is not str or len(raw.encode("utf-8")) > _MAX_MESSAGE:
        raise ValueError("protocol_error")
    value: object = json.loads(raw, object_pairs_hook=_object, parse_constant=_constant)
    if type(value) is not dict or type(value.get("type")) is not str:
        raise ValueError("protocol_error")
    kind: str = value["type"]
    return kind


async def _cleanup(socket: ClientConnection) -> None:
    try:
        async with asyncio.timeout(_CLEANUP_SECONDS):
            await socket.close()
    except BaseException:
        # Never retain/log a peer's close reason or exception. Aborting the owned
        # transport prevents an expired close handshake from leaking a socket.
        socket.transport.abort()
        raise


async def _drain(task: asyncio.Task[None]) -> bool:
    """Finish an owned task even if the waiter is repeatedly cancelled."""
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
        except Exception:
            break
    if not task.cancelled():
        # Retrieve BaseExceptions as well; process-control exceptions propagate.
        task.result()
    return cancelled


class HAWebSocketClient:
    """Own one finite asyncio lifecycle. Await run and close from the same loop."""

    __slots__ = ("_configuration", "_health", "_loop", "_started", "_closed",
                 "_worker", "_closer")

    def __init__(self, configuration: HAConfiguration) -> None:
        if hasattr(self, "_configuration"):
            raise RuntimeError("client_initialized")
        if type(configuration) is not HAConfiguration:
            raise TypeError("invalid_configuration")
        self._configuration = configuration
        self._health = HAConnectionHealth()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._started = False
        self._closed = False
        self._worker: asyncio.Task[None] | None = None
        self._closer: asyncio.Task[None] | None = None

    def __repr__(self) -> str:
        return "HAWebSocketClient(<redacted>)"

    def __getstate__(self) -> NoReturn:
        raise TypeError("client_serialization_refused")

    def __reduce__(self) -> NoReturn:
        raise TypeError("client_serialization_refused")

    def health(self) -> HAConnectionHealth:
        return self._health

    def _bind(self) -> None:
        loop = asyncio.get_running_loop()
        if self._loop is not None and self._loop is not loop:
            raise RuntimeError("wrong_event_loop")
        self._loop = loop

    def _publish(self, state: str, reason: str | None = None, *,
                 attempt: int | None = None) -> None:
        if self._closed and state != "closed":
            return
        self._health = HAConnectionHealth(
            state, reason,
            self._health.reconnect_attempt if attempt is None else attempt,
            self._health.sequence + 1,
        )

    async def run(self) -> None:
        self._bind()
        if self._closed:
            raise RuntimeError("client_closed")
        if self._started:
            raise RuntimeError("client_started")
        self._started = True
        worker = asyncio.create_task(self._run(), name="ha-websocket-lifecycle")
        self._worker = worker
        try:
            await asyncio.shield(worker)
        except asyncio.CancelledError:
            if not self._closed:
                worker.cancel()
            await _drain(worker)
            if not self._closed and self._health.reason != "cancelled":
                self._publish("disconnected", "cancelled")
            current = asyncio.current_task()
            if not self._closed or (current is not None and current.cancelling()):
                raise

    async def aclose(self) -> None:
        self._bind()
        if self._closer is None:
            self._closed = True
            self._publish("closed")
            if self._worker is not None and not self._worker.done():
                self._worker.cancel()
            self._closer = asyncio.create_task(self._finish_close(), name="ha-websocket-close")
        # Cancellation of this waiter does not cancel the owned drain.
        await asyncio.shield(self._closer)

    async def _finish_close(self) -> None:
        if self._worker is not None:
            await _drain(self._worker)

    async def _attempt(self) -> str:
        socket: ClientConnection | None = None
        reason = "internal_error"
        try:
            deadline = _clock() + self._configuration.request_timeout_ms / 1000
            async with asyncio.timeout_at(deadline):
                socket = await _connect(self._configuration)
                self._publish("authenticating")
                kind = _message_type(await socket.recv())
                if kind == "auth_invalid":
                    return "auth_failed"
                if kind != "auth_required":
                    return "protocol_error"
                await socket.send(json.dumps({"type": "auth", "access_token":
                                              self._configuration.access_token_for_transport()}))
                kind = _message_type(await socket.recv())
                if kind == "auth_invalid":
                    return "auth_failed"
                if kind != "auth_ok":
                    return "protocol_error"
                if _clock() >= deadline:
                    raise TimeoutError
            self._publish("connected")
            # Without subscriptions there are no valid application messages.
            # Control frames/keepalive are consumed internally by websockets.
            await socket.recv()
            reason = "protocol_error"
        except TimeoutError:
            reason = "timeout"
        except InvalidStatus as error:
            reason = "auth_failed" if error.response.status_code in (401, 403) else "protocol_error"
        except ConnectionClosed as error:
            # 1007/1009 indicate invalid data/message size, not transient loss.
            reason = ("protocol_error" if error.sent is not None
                      and error.sent.code in (1002, 1007, 1009) else "transport_failed")
        except (OSError, EOFError):
            reason = "transport_failed"
        except (InvalidHandshake, ValueError, UnicodeError, RecursionError):
            reason = "protocol_error"
        except Exception:
            reason = "internal_error"
        finally:
            if socket is not None:
                cleanup = asyncio.create_task(_cleanup(socket), name="ha-websocket-cleanup")
                interrupted = False
                try:
                    interrupted = await _drain(cleanup)
                except Exception:
                    pass  # Owned transport is aborted; never mask original outcome.
                if interrupted:
                    raise asyncio.CancelledError
        return reason

    async def _run(self) -> None:
        delays = self._configuration.reconnect_delays_ms()
        attempt = 0
        try:
            while not self._closed:
                self._publish("connecting", attempt=attempt)
                reason = await self._attempt()
                if self._closed:
                    return
                if reason == "auth_failed":
                    self._publish("auth_failed", reason)
                    return
                if reason not in ("transport_failed", "timeout"):
                    self._publish("failed", reason)
                    return
                self._publish("disconnected", reason)
                if attempt == len(delays):
                    self._publish("failed", "reconnect_exhausted")
                    return
                delay = delays[attempt]
                attempt += 1
                self._publish("reconnecting", reason, attempt=attempt)
                await _sleep(delay / 1000)
        except asyncio.CancelledError:
            self._publish("disconnected", "cancelled")
            raise
        finally:
            if self._closed and self._health.state != "closed":
                self._publish("closed")
