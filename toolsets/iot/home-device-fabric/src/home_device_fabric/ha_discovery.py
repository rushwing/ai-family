"""Bounded read-only HA discovery; private provider data stays adapter-local.

Completeness means four credential-visible responses, not an atomic/global HA
snapshot. Repr and errors are safe; for_mapping is a deliberate private export.
"""

from __future__ import annotations

import asyncio
import json
import math
from dataclasses import dataclass
from typing import NoReturn, cast

from websockets.asyncio.client import ClientConnection
from websockets.exceptions import ConnectionClosed, InvalidHandshake, InvalidStatus

from .ha_configuration import HAConfiguration
from .ha_websocket import _WIRE_LOGGER, _cleanup, _drain, _NoRedirectConnect, _tls_context

__all__ = ["HARegistryDiscoveryClient", "HADiscoverySnapshot", "HADiscoveryError"]

_COMPONENTS = ("devices", "entities", "areas", "states")
_COMMANDS = (
    "config/device_registry/list",
    "config/entity_registry/list",
    "config/area_registry/list",
    "get_states",
)
_STAGES = ("operation", "auth", *_COMPONENTS, "cleanup")
_CODES = frozenset(
    (
        "auth_failed",
        "permission_denied",
        "unsupported_command",
        "command_failed",
        "invalid_response",
        "response_limit",
        "timeout",
        "transport_failed",
        "internal_error",
        "cleanup_failed",
        "client_busy",
        "client_closed",
    )
)


class HADiscoveryError(Exception):
    """Immutable finite diagnostics, with no raw payload or nested exception."""

    __slots__ = ("_code", "_stage", "_completed")
    _code: str
    _stage: str
    _completed: tuple[str, ...]

    def __init__(self, code: str, stage: str = "operation", completed: tuple[str, ...] = ()):
        if (
            type(code) is not str
            or code not in _CODES
            or type(stage) is not str
            or stage not in _STAGES
            or type(completed) is not tuple
            or any(type(label) is not str for label in completed)
            or completed != _COMPONENTS[: len(completed)]
        ):
            raise ValueError("invalid_diagnostic")
        if hasattr(self, "_code"):
            raise AttributeError("immutable_discovery_error")
        object.__setattr__(self, "_code", code)
        object.__setattr__(self, "_stage", stage)
        object.__setattr__(self, "_completed", completed)
        super().__init__(code + ": " + stage)

    @property
    def code(self) -> str:
        return self._code

    @property
    def stage(self) -> str:
        return self._stage

    @property
    def completed(self) -> tuple[str, ...]:
        return self._completed

    def to_dict(self) -> dict[str, object]:
        return {"code": self.code, "stage": self.stage, "completed": list(self.completed)}

    def __repr__(self) -> str:
        return f"HADiscoveryError({self.to_dict()!r})"

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
        raise AttributeError("immutable_discovery_error")

    def __delattr__(self, name: str) -> NoReturn:
        raise AttributeError("immutable_discovery_error")

    def __reduce__(self) -> NoReturn:
        raise TypeError("discovery_error_serialization_forbidden")


@dataclass(frozen=True, slots=True, repr=False)
class HADiscoverySnapshot:
    """Internal typed record. Raw export is for trusted mapper composition only."""

    _payloads: tuple[str, ...]
    _counts: tuple[int, ...]

    def for_mapping(self) -> dict[str, list[dict[str, object]]]:
        return {
            label: json.loads(raw) for label, raw in zip(_COMPONENTS, self._payloads, strict=True)
        }

    def to_redacted_dict(self) -> dict[str, object]:
        return {"complete": True, "counts": dict(zip(_COMPONENTS, self._counts, strict=True))}

    def __repr__(self) -> str:
        return "HADiscoverySnapshot(<redacted>)"

    def __reduce__(self) -> NoReturn:
        raise TypeError("raw_discovery_snapshot_serialization_forbidden")


class _Limit(ValueError):
    pass


class _Rejected(ValueError):
    pass


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        key.encode("utf-8")  # JSON escapes must not smuggle unpaired surrogates.
        if key in result:
            raise ValueError("invalid_response")
        result[key] = value
    return result


def _constant(value: str) -> NoReturn:
    raise ValueError("invalid_response")


def _number(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("invalid_response")
    return result


def _decode(raw: str | bytes, limit: int) -> dict[str, object]:
    if type(raw) is not str:
        raise ValueError("invalid_response")
    if len(raw.encode("utf-8")) > limit:
        raise _Limit()
    value: object = json.loads(
        raw, object_pairs_hook=_pairs, parse_constant=_constant, parse_float=_number
    )
    pending = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        if depth > 32:
            raise _Limit()
        if type(item) is dict:
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            item.encode("utf-8")
    if type(value) is not dict:
        raise ValueError("invalid_response")
    return cast(dict[str, object], value)


def _text(value: object, limit: int = 512, *, empty: bool = False) -> bool:
    return type(value) is str and (0 if empty else 1) <= len(value) <= limit


def _records(value: object, component: str, limit: int) -> list[dict[str, object]]:
    if type(value) is not list:
        raise ValueError("invalid_response")
    if len(value) > limit:
        raise _Limit()
    identity = {
        "devices": "id",
        "entities": "entity_id",
        "areas": "area_id",
        "states": "entity_id",
    }[component]
    seen: set[str] = set()
    for row in value:
        if type(row) is not dict or not _text(row.get(identity)):
            raise ValueError("invalid_response")
        identifier = cast(str, row[identity])
        if identifier in seen:
            raise ValueError("invalid_response")
        seen.add(identifier)
        for name in ("device_id", "area_id"):
            if name in row and row[name] is not None and not _text(row[name]):
                raise ValueError("invalid_response")
        if component == "areas" and not _text(row.get("name")):
            raise ValueError("invalid_response")
        if component == "states" and (
            not _text(row.get("state"), 4096, empty=True) or type(row.get("attributes")) is not dict
        ):
            raise ValueError("invalid_response")
    return cast(list[dict[str, object]], value)


async def _open(configuration: HAConfiguration, limit: int) -> ClientConnection:
    secure = configuration.base_url.startswith("https:")
    uri = ("wss:" if secure else "ws:") + configuration.base_url.split(":", 1)[1] + "/api/websocket"
    return await _NoRedirectConnect(
        uri,
        proxy=None,
        compression=None,
        additional_headers=None,
        user_agent_header=None,
        open_timeout=configuration.request_timeout_ms / 1000,
        close_timeout=1,
        ping_interval=20,
        ping_timeout=20,
        max_size=limit,
        max_queue=4,
        logger=_WIRE_LOGGER,
        ssl=_tls_context() if secure else None,
    )


class HARegistryDiscoveryClient:
    """One fresh socket per call; no implicit retry or shared subscription reader."""

    __slots__ = ("_configuration", "_bytes", "_records", "_loop", "_worker", "_closed", "_closer")

    def __init__(
        self,
        configuration: HAConfiguration,
        *,
        max_response_bytes: int = 262144,
        max_records: int = 2048,
    ) -> None:
        if hasattr(self, "_configuration"):
            raise RuntimeError("client_initialized")
        if type(configuration) is not HAConfiguration:
            raise TypeError("invalid_configuration")
        if type(max_response_bytes) is not int or not 4096 <= max_response_bytes <= 4194304:
            raise ValueError("invalid_byte_limit")
        if type(max_records) is not int or not 1 <= max_records <= 10000:
            raise ValueError("invalid_record_limit")
        self._configuration = configuration
        self._bytes = max_response_bytes
        self._records = max_records
        self._loop: asyncio.AbstractEventLoop | None = None
        self._worker: asyncio.Task[HADiscoverySnapshot] | None = None
        self._closed = False
        self._closer: asyncio.Task[None] | None = None

    def __repr__(self) -> str:
        return "HARegistryDiscoveryClient(<redacted>)"

    def __reduce__(self) -> NoReturn:
        raise TypeError("raw_discovery_client_serialization_forbidden")

    def _bind(self) -> asyncio.AbstractEventLoop:
        loop = asyncio.get_running_loop()
        if self._loop is not None and self._loop is not loop:
            raise RuntimeError("wrong_event_loop")
        self._loop = loop
        return loop

    async def __aenter__(self) -> HARegistryDiscoveryClient:
        self._bind()
        if self._closed:
            raise HADiscoveryError("client_closed")
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        await self.aclose()

    async def discover(self) -> HADiscoverySnapshot:
        loop = self._bind()
        if self._closed:
            raise HADiscoveryError("client_closed")
        if self._worker is not None:
            raise HADiscoveryError("client_busy")
        deadline = loop.time() + self._configuration.request_timeout_ms / 1000
        worker = asyncio.create_task(self._collect(deadline), name="ha-discovery")
        self._worker = worker
        try:
            return await asyncio.shield(worker)
        except asyncio.CancelledError:
            worker.cancel()
            # Drain in a separate task so repeated waiter cancellation cannot
            # inject a second cancellation into socket cleanup.
            drain = asyncio.create_task(self._finish(worker), name="ha-discovery-drain")
            await _drain(drain)
            raise
        finally:
            self._worker = None

    async def aclose(self) -> None:
        self._bind()
        if self._closer is None:
            self._closed = True
            worker = self._worker
            if worker is not None and not worker.done():
                worker.cancel()
            self._closer = asyncio.create_task(self._finish(worker), name="ha-discovery-close")
        await asyncio.shield(self._closer)

    async def _finish(self, worker: asyncio.Task[HADiscoverySnapshot] | None) -> None:
        if worker is not None:
            while not worker.done():
                try:
                    await asyncio.shield(worker)
                except asyncio.CancelledError:
                    continue
                except Exception:
                    break
            if not worker.cancelled():
                try:
                    worker.result()
                except BaseException:
                    pass  # The discovery waiter owns its original outcome.

    async def _collect(self, deadline: float) -> HADiscoverySnapshot:
        socket: ClientConnection | None = None
        stage = "auth"
        completed: tuple[str, ...] = ()
        payloads: list[str] = []
        counts: list[int] = []
        code: str | None = None
        cancelled = False
        try:
            async with asyncio.timeout_at(deadline):
                socket = await _open(self._configuration, self._bytes)
                hello = _decode(await socket.recv(), self._bytes)
                if hello.get("type") == "auth_invalid":
                    raise _Rejected("auth_failed")
                if hello.get("type") != "auth_required":
                    raise ValueError("invalid_response")
                if asyncio.get_running_loop().time() >= deadline:
                    raise TimeoutError()
                await socket.send(
                    json.dumps(
                        {
                            "type": "auth",
                            "access_token": self._configuration.access_token_for_transport(),
                        }
                    )
                )
                auth = _decode(await socket.recv(), self._bytes)
                if auth.get("type") == "auth_invalid":
                    raise _Rejected("auth_failed")
                if auth.get("type") != "auth_ok":
                    raise ValueError("invalid_response")
                if asyncio.get_running_loop().time() >= deadline:
                    raise TimeoutError()
                for identifier, (stage, command) in enumerate(zip(_COMPONENTS, _COMMANDS), 1):
                    await socket.send(json.dumps({"id": identifier, "type": command}))
                    result = _decode(await socket.recv(), self._bytes)
                    if (
                        type(result.get("id")) is not int
                        or result["id"] != identifier
                        or result.get("type") != "result"
                        or type(result.get("success")) is not bool
                    ):
                        raise ValueError("invalid_response")
                    if result["success"] is False:
                        error = result.get("error")
                        if type(error) is not dict or not _text(error.get("code")):
                            raise ValueError("invalid_response")
                        failure = error["code"]
                        raise _Rejected(
                            "permission_denied"
                            if failure in ("unauthorized", "not_allowed")
                            else "unsupported_command"
                            if failure == "unknown_command"
                            else "command_failed"
                        )
                    records = _records(result.get("result"), stage, self._records)
                    payloads.append(json.dumps(records, allow_nan=False, separators=(",", ":")))
                    counts.append(len(records))
                    completed += (stage,)
                    if asyncio.get_running_loop().time() >= deadline:
                        raise TimeoutError()
        except asyncio.CancelledError:
            cancelled = True
        except TimeoutError:
            code = "timeout"
        except _Limit:
            code = "response_limit"
        except _Rejected as error:
            code = str(error)
        except InvalidStatus as error:
            code = "auth_failed" if error.response.status_code in (401, 403) else "invalid_response"
        except ConnectionClosed as error:
            code = (
                "response_limit"
                if error.sent is not None and error.sent.code == 1009
                else "invalid_response"
                if error.sent is not None and error.sent.code in (1002, 1007)
                else "transport_failed"
            )
        except (OSError, EOFError):
            code = "transport_failed"
        except (ValueError, UnicodeError, RecursionError, InvalidHandshake):
            code = "invalid_response"
        except Exception:
            code = "internal_error"
        finally:
            if socket is not None:
                cleanup = asyncio.create_task(_cleanup(socket), name="ha-discovery-cleanup")
                try:
                    cancelled = await _drain(cleanup) or cancelled
                except Exception:
                    if code is None:
                        code, stage = "cleanup_failed", "cleanup"
        if cancelled:
            raise asyncio.CancelledError() from None
        if self._closed:
            raise HADiscoveryError("client_closed", "operation", completed)
        if code is None and asyncio.get_running_loop().time() >= deadline:
            code, stage = "timeout", "cleanup"
        if code is not None:
            raise HADiscoveryError(code, stage, completed) from None
        return HADiscoverySnapshot(tuple(payloads), tuple(counts))
