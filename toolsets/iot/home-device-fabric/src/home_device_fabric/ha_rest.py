"""Bounded read-only HA metadata. Secrets exist only in private transport work.

The asyncio wrapper is single-operation; close drains via an operation event.
Wire/debug tracing, private introspection and traceback-frame locals are outside
its supported diagnostic boundary. No client or exception stores raw responses.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import NoReturn, SupportsIndex, cast

import httpx

from .ha_configuration import HAConfiguration

__all__ = ["HARestClient", "HARuntimeInfo", "HARestError"]

_CODES = frozenset(("auth_failed", "timeout", "transport_failed", "http_error",
                    "invalid_response", "client_closed", "client_busy", "invalid_correlation_id"))
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", re.ASCII)
_BODY_LIMIT = 262144
_CLEANUP_SECONDS = 1.0


def _valid_id(value: object) -> bool:
    return type(value) is str and _ID.fullmatch(value) is not None


def _valid_version(value: object) -> bool:
    return (type(value) is str and 1 <= len(value) <= 128
            and all(33 <= ord(char) <= 126 for char in value))


class HARuntimeInfo:
    """Immutable adapter-local metadata; exports contain only validated version."""

    __slots__ = ("__version",)
    __version: str

    def __init__(self, version: str) -> None:
        if hasattr(self, "_HARuntimeInfo__version"):
            raise AttributeError("immutable_runtime_info")
        if not _valid_version(version):
            raise ValueError("invalid_version")
        object.__setattr__(self, "_HARuntimeInfo__version", version)

    @property
    def version(self) -> str:
        return self.__version

    def to_dict(self) -> dict[str, str]:
        return {"version": self.__version}

    def __repr__(self) -> str:
        return "HARuntimeInfo(<redacted>)"

    def __reduce__(self) -> tuple[type[HARuntimeInfo], tuple[str]]:
        return HARuntimeInfo, (self.__version,)

    def __setattr__(self, name: str, value: object) -> NoReturn:
        raise AttributeError("immutable_runtime_info")

    def __delattr__(self, name: str) -> NoReturn:
        raise AttributeError("immutable_runtime_info")


class HARestError(Exception):
    """Finite value-free category plus validated caller correlation metadata."""

    __slots__ = ("__code", "__correlation_id", "__http_status")
    __code: str
    __correlation_id: str | None
    __http_status: int | None

    def __init__(self, code: str, *, correlation_id: str | None = None,
                 http_status: int | None = None) -> None:
        if (
            type(code) is not str or code not in _CODES
            or (code == "invalid_correlation_id" and correlation_id is not None)
            or (code != "invalid_correlation_id" and not _valid_id(correlation_id))
            or (code == "auth_failed" and (type(http_status) is not int or http_status != 401))
            or (code == "http_error" and http_status is not None
                and (type(http_status) is not int
                     or not 100 <= http_status <= 599 or http_status in (200, 401)))
            or (code not in ("auth_failed", "http_error") and http_status is not None)
        ):
            raise ValueError("invalid_diagnostic")
        if hasattr(self, "_HARestError__code"):
            raise AttributeError("immutable_rest_error")
        object.__setattr__(self, "_HARestError__code", code)
        object.__setattr__(self, "_HARestError__correlation_id", correlation_id)
        object.__setattr__(self, "_HARestError__http_status", http_status)
        super().__init__(code)

    @property
    def code(self) -> str:
        return self.__code

    @property
    def correlation_id(self) -> str | None:
        return self.__correlation_id

    @property
    def http_status(self) -> int | None:
        return self.__http_status

    def to_dict(self) -> dict[str, str | int | None]:
        return {"code": self.__code, "correlation_id": self.__correlation_id,
                "http_status": self.__http_status}

    def __repr__(self) -> str:
        return f"HARestError({self.to_dict()!r})"

    def __reduce__(self) -> tuple[object, tuple[str, str | None, int | None]]:
        # Serialize only the validated projection, never exception bookkeeping.
        return _restore_error, (self.__code, self.__correlation_id, self.__http_status)

    def __setattr__(self, name: str, value: object) -> None:
        # Python and traceback tools may attach exception bookkeeping. The
        # transport never assigns raw exceptions to any of these surfaces.
        if name in ("__traceback__", "__context__", "__cause__", "__suppress_context__",
                    "__notes__"):
            super().__setattr__(name, value)
            return
        raise AttributeError("immutable_rest_error")

    def __delattr__(self, name: str) -> NoReturn:
        raise AttributeError("immutable_rest_error")


def _restore_error(code: str, correlation_id: str | None, http_status: int | None) -> HARestError:
    return HARestError(code, correlation_id=correlation_id, http_status=http_status)


def _clock() -> float:
    return asyncio.get_running_loop().time()


class _WireClient:
    """Owned HTTPX transport, without AsyncClient's URL-bearing INFO logger.

    Calling the documented transport API directly also eliminates redirect and
    cookie/session machinery. HTTP core DEBUG tracing is deliberately excluded.
    """

    def __init__(self) -> None:
        self._transport = httpx.AsyncHTTPTransport(
            verify=True, trust_env=False, retries=0, http1=True, http2=False,
        )

    async def send(self, request: httpx.Request) -> httpx.Response:
        return await self._transport.handle_async_request(request)

    async def aclose(self) -> None:
        await self._transport.aclose()


def _make_client() -> _WireClient:
    return _WireClient()


def _object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_key")
        result[key] = value
    return result


def _constant(value: str) -> NoReturn:
    raise ValueError("non_finite_json")


def _version(body: bytes, configuration: HAConfiguration) -> str | None:
    try:
        parsed: object = json.loads(body.decode("utf-8"), object_pairs_hook=_object,
                                    parse_constant=_constant)
    except (ValueError, UnicodeError, RecursionError):
        return None
    if type(parsed) is not dict:
        return None
    value: object = parsed.get("version")
    if not _valid_version(value):
        return None
    value = cast(str, value)
    if configuration.access_token_for_transport() in value or configuration.base_url in value:
        return None
    return value


def _media_valid(response: httpx.Response) -> bool:
    # Full-match a narrow JSON media language; parameters cannot override each
    # other or hide a second Content-Type. Duplicate headers combine with commas.
    media = response.headers.get("content-type", "")
    if re.fullmatch(r'\s*application/json\s*(?:;\s*charset\s*=\s*(?:utf-8|"utf-8")\s*)?',
                    media, re.IGNORECASE | re.ASCII) is None:
        return False
    encoding = response.headers.get("content-encoding")
    return encoding is None or encoding.strip().lower() == "identity"


class _Operation:
    def __init__(self, configuration: HAConfiguration, deadline: float) -> None:
        self.configuration = configuration
        self.deadline = deadline
        self.client: _WireClient | None = None
        self.response: httpx.Response | None = None

    async def read(self) -> tuple[str | None, int | None, str | None]:
        self.client = _make_client()
        remaining = max(0.0, self.deadline - _clock())
        if remaining == 0:
            return "timeout", None, None
        request = httpx.Request(
            "GET", self.configuration.base_url + "/api/config",
            headers={"Authorization": "Bearer " + self.configuration.access_token_for_transport(),
                     "Accept": "application/json", "Accept-Encoding": "identity"},
            extensions={"timeout": dict.fromkeys(("connect", "read", "write", "pool"), remaining)},
        )
        self.response = await self.client.send(request)
        status = self.response.status_code
        if status == 401:
            return "auth_failed", 401, None
        if status != 200:
            diagnostic_status = status if type(status) is int and 100 <= status <= 599 else None
            return "http_error", diagnostic_status, None
        if not _media_valid(self.response):
            return "invalid_response", None, None
        body = bytearray()
        if not isinstance(self.response.stream, httpx.AsyncByteStream):
            return "invalid_response", None, None
        # Response.aiter_raw auto-closes at exhaustion. Consume the raw public
        # transport stream so *all* close waits use the separate cleanup guard.
        async for chunk in self.response.stream:
            if len(body) + len(chunk) > _BODY_LIMIT:
                return "invalid_response", None, None
            body.extend(chunk)
        value = _version(bytes(body), self.configuration)
        return (None, None, value) if value is not None else ("invalid_response", None, None)

    async def cleanup(self) -> str | None:
        failed = False
        try:
            async with asyncio.timeout(_CLEANUP_SECONDS):
                # Start both owned closes under one aggregate guard. A slow
                # response close must not prevent a transport-close attempt.
                results = await asyncio.gather(
                    *(resource.aclose() for resource in (self.response, self.client)
                      if resource is not None), return_exceptions=True,
                )
                failed = any(isinstance(result, BaseException) for result in results)
        except TimeoutError:
            return "timeout"
        finally:
            self.response = None
            self.client = None
        return "transport_failed" if failed else None


class HARestClient:
    """One operation per asyncio wrapper; close drains an operation event."""

    __slots__ = ("__configuration", "__closed", "__done")
    __configuration: HAConfiguration
    __closed: bool
    __done: asyncio.Event | None

    def __init__(self, configuration: HAConfiguration) -> None:
        if hasattr(self, "_HARestClient__configuration"):
            raise AttributeError("immutable_rest_client")
        if type(configuration) is not HAConfiguration:
            raise TypeError("invalid_configuration")
        object.__setattr__(self, "_HARestClient__configuration", configuration)
        object.__setattr__(self, "_HARestClient__closed", False)
        object.__setattr__(self, "_HARestClient__done", None)

    def __repr__(self) -> str:
        return "HARestClient(<redacted>)"

    def __setattr__(self, name: str, value: object) -> NoReturn:
        raise AttributeError("immutable_rest_client")

    def __delattr__(self, name: str) -> NoReturn:
        raise AttributeError("immutable_rest_client")

    def __getstate__(self) -> NoReturn:
        raise TypeError("raw_rest_client_serialization_forbidden")

    def __reduce__(self) -> NoReturn:
        raise TypeError("raw_rest_client_serialization_forbidden")

    def __reduce_ex__(self, protocol: SupportsIndex) -> NoReturn:
        raise TypeError("raw_rest_client_serialization_forbidden")

    async def __aenter__(self) -> HARestClient:
        if self.__closed:
            raise RuntimeError("client_closed")
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        object.__setattr__(self, "_HARestClient__closed", True)
        done = self.__done
        if done is not None:
            await done.wait()  # Never await the caller's task or relay its error.

    async def runtime_info(self, *, correlation_id: str) -> HARuntimeInfo:
        config = self.__configuration
        if (not _valid_id(correlation_id) or config.access_token_for_transport() in correlation_id
                or config.base_url in correlation_id):
            raise HARestError("invalid_correlation_id")
        if self.__closed:
            raise HARestError("client_closed", correlation_id=correlation_id)
        if self.__done is not None:
            raise HARestError("client_busy", correlation_id=correlation_id)
        done = asyncio.Event()
        object.__setattr__(self, "_HARestClient__done", done)
        deadline = _clock() + config.request_timeout_ms / 1000
        operation = _Operation(config, deadline)
        code: str | None = None
        status: int | None = None
        value: str | None = None
        cancelled = False
        try:
            try:
                async with asyncio.timeout_at(deadline):
                    code, status, value = await operation.read()
            except asyncio.CancelledError:
                cancelled = True
            except (TimeoutError, httpx.TimeoutException):
                code = "timeout"
            except Exception:
                # Discard library exceptions *before* constructing the public
                # error. Suppressing traceback display alone retains context.
                code = "transport_failed"
            cleanup = asyncio.create_task(operation.cleanup())
            while not cleanup.done():
                try:
                    await asyncio.shield(cleanup)
                except asyncio.CancelledError:
                    cancelled = True
            cleanup_code = cleanup.result()
            if cleanup_code == "timeout" or (
                cleanup_code is not None and code is None and value is None
            ):
                code, status = cleanup_code, None
            if _clock() >= deadline:
                code, status = "timeout", None
        finally:
            object.__setattr__(self, "_HARestClient__done", None)
            done.set()
        if cancelled:
            raise asyncio.CancelledError()
        if code is not None:
            raise HARestError(code, correlation_id=correlation_id, http_status=status)
        if value is None:
            raise HARestError("invalid_response", correlation_id=correlation_id)
        return HARuntimeInfo(value)
