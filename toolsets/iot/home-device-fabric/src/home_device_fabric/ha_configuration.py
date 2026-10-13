"""Offline, immutable HA inputs; only the explicit transport accessor reveals tokens.

Slots and redacted representations protect supported diagnostics, not deliberate
private introspection, debugger access or process memory. No connection is made.
"""

from __future__ import annotations

import ipaddress
import json
import re
from typing import NoReturn, SupportsIndex

__all__ = ["HAConfiguration", "HAConfigurationError"]

_MISSING = object()
_FIELDS = (
    "schema_version", "base_url", "request_timeout_ms", "reconnect_initial_delay_ms",
    "reconnect_max_delay_ms", "reconnect_max_attempts",
)
_LIMITS = (
    ("request_timeout_ms", 1, 120_000, 10_000),
    ("reconnect_initial_delay_ms", 1, 60_000, 1_000),
    ("reconnect_max_delay_ms", 1, 300_000, 30_000),
    ("reconnect_max_attempts", 1, 32, 8),
)
_CODES = frozenset((
    "invalid_settings", "unknown_field", "missing_field", "invalid_setting",
    "unsupported_version", "out_of_bounds", "invalid_endpoint", "missing_token",
    "invalid_token", "invalid_reconnect_order",
))
_PATH_PARTS = frozenset((*_FIELDS, "settings", "access_token", "<unknown>"))


class HAConfigurationError(ValueError):
    """Fixed category and structural path; never contains a submitted value."""

    def __init__(self, code: str, path: tuple[str, ...]) -> None:
        if (
            type(code) is not str or code not in _CODES or type(path) is not tuple
            or not path or any(type(part) is not str or part not in _PATH_PARTS for part in path)
        ):
            raise ValueError("invalid_diagnostic")
        self.code = code
        self.path = path
        super().__init__(code + ": " + ".".join(path))


def _fail(code: str, *path: str) -> NoReturn:
    raise HAConfigurationError(code, path)


def _endpoint(value: str) -> str | None:
    # Fully enumerate authority/root syntax instead of inheriting URL-parser
    # repairs (empty delimiters, userinfo, alternate IPv4 forms, backslashes).
    if not 1 <= len(value) <= 2048 or any(not 33 <= ord(c) <= 126 for c in value):
        return None
    match = re.fullmatch(r"(?i)(https?)://([^/?#@%\\]+)(/?)", value)
    if match is None:
        return None
    scheme, authority = match.group(1).lower(), match.group(2)
    port = ""
    if authority.startswith("["):
        close = authority.find("]")
        if close < 0:
            return None
        host = authority[1:close]
        remainder = authority[close + 1:]
        if remainder:
            if not remainder.startswith(":"):
                return None
            port = remainder[1:]
            if not port:
                return None
        try:
            ipaddress.IPv6Address(host)
        except ValueError:
            return None  # Caller raises fixed error outside this exception handler.
        host = "[" + host.lower() + "]"
    else:
        if authority.count(":") > 1 or "[" in authority or "]" in authority:
            return None
        host, separator, port = authority.partition(":")
        if separator and not port:
            return None
        if not host or len(host) > 253:
            return None
        labels = host.split(".")
        if re.fullmatch(r"(?i)(?:[0-9]+|0x[0-9a-f]+)(?:\.(?:[0-9]+|0x[0-9a-f]+))*", host):
            try:
                ipaddress.IPv4Address(host)
            except ValueError:
                return None
        elif any(
            not 1 <= len(label) <= 63
            or re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?", label) is None
            for label in labels
        ):
            return None
        host = host.lower()
    if port:
        if not port.isascii() or not port.isdecimal():
            return None
        # Bound conversion before int: URL length is finite, but this also avoids
        # dependence on Python's interpreter-wide integer digit conversion limit.
        significant = port.lstrip("0")
        if not significant or len(significant) > 5 or int(significant) > 65535:
            return None
    return scheme + "://" + host + (":" + port if port else "")


class _Credential:
    __slots__ = ("__value",)
    __value: str

    def __init__(self, value: str) -> None:
        object.__setattr__(self, "_Credential__value", value)

    def __setattr__(self, name: str, value: object) -> NoReturn:
        raise AttributeError("immutable_credential")

    def __delattr__(self, name: str) -> NoReturn:
        raise AttributeError("immutable_credential")

    def __repr__(self) -> str:
        return "<redacted>"

    def for_transport(self) -> str:
        return self.__value

    def __getstate__(self) -> NoReturn:
        raise TypeError("raw_credential_serialization_forbidden")

    def __reduce__(self) -> NoReturn:
        raise TypeError("raw_credential_serialization_forbidden")

    def __reduce_ex__(self, protocol: SupportsIndex) -> NoReturn:
        raise TypeError("raw_credential_serialization_forbidden")


class HAConfiguration:
    """Validated explicit settings; snapshots are safe, transport inputs deliberate.

    Only plain dict/string/integer inputs are accepted. No user-defined coercion,
    subclass hooks or implicit lookup runs during validation.
    """

    __slots__ = ("__endpoint", "__numbers", "__credential")
    __endpoint: str
    __numbers: tuple[int, ...]
    __credential: _Credential

    def __init__(self, settings: object, *, access_token: object = _MISSING) -> None:
        # An explicit repeated __init__ call must not mutate an existing instance.
        if hasattr(self, "_HAConfiguration__credential"):
            raise AttributeError("immutable_configuration")
        if type(settings) is not dict:
            _fail("invalid_settings", "settings")
        if any(type(key) is not str for key in settings):
            _fail("invalid_settings", "settings")
        if any(key not in _FIELDS for key in settings):
            _fail("unknown_field", "settings", "<unknown>")
        for required in ("schema_version", "base_url"):
            if required not in settings:
                _fail("missing_field", "settings", required)
        version = settings["schema_version"]
        if type(version) is not int:
            _fail("invalid_setting", "settings", "schema_version")
        if version != 1:
            _fail("unsupported_version", "settings", "schema_version")
        url = settings["base_url"]
        if type(url) is not str:
            _fail("invalid_setting", "settings", "base_url")
        endpoint = _endpoint(url)
        if endpoint is None:
            _fail("invalid_endpoint", "settings", "base_url")
        numbers: list[int] = []
        for name, minimum, maximum, default in _LIMITS:
            value = settings.get(name, default)
            if type(value) is not int:
                _fail("invalid_setting", "settings", name)
            if not minimum <= value <= maximum:
                _fail("out_of_bounds", "settings", name)
            numbers.append(value)
        if numbers[1] > numbers[2]:
            _fail("invalid_reconnect_order", "settings", "reconnect_max_delay_ms")
        if access_token is _MISSING:
            _fail("missing_token", "access_token")
        if (
            type(access_token) is not str or not 1 <= len(access_token) <= 8192
            or any(not 33 <= ord(c) <= 126 for c in access_token)
        ):
            _fail("invalid_token", "access_token")
        object.__setattr__(self, "_HAConfiguration__endpoint", endpoint)
        object.__setattr__(self, "_HAConfiguration__numbers", tuple(numbers))
        object.__setattr__(self, "_HAConfiguration__credential", _Credential(access_token))

    def __setattr__(self, name: str, value: object) -> NoReturn:
        raise AttributeError("immutable_configuration")

    def __delattr__(self, name: str) -> NoReturn:
        raise AttributeError("immutable_configuration")

    @property
    def schema_version(self) -> int:
        return 1

    @property
    def base_url(self) -> str:
        """Validated connection root; omitted from ordinary diagnostics."""
        return self.__endpoint

    @property
    def request_timeout_ms(self) -> int:
        return self.__numbers[0]

    @property
    def reconnect_initial_delay_ms(self) -> int:
        return self.__numbers[1]

    @property
    def reconnect_max_delay_ms(self) -> int:
        return self.__numbers[2]

    @property
    def reconnect_max_attempts(self) -> int:
        return self.__numbers[3]

    def access_token_for_transport(self) -> str:
        """Deliberately reveal credential to trusted transport composition only."""
        return self.__credential.for_transport()

    def reconnect_delays_ms(self) -> tuple[int, ...]:
        return tuple(
            min(self.reconnect_initial_delay_ms * 2**i, self.reconnect_max_delay_ms)
            for i in range(self.reconnect_max_attempts)
        )

    def to_redacted_dict(self) -> dict[str, int | str]:
        return {
            "schema_version": 1,
            "base_url": "<redacted-endpoint>",
            "access_token": "<redacted>",
            "request_timeout_ms": self.request_timeout_ms,
            "reconnect_initial_delay_ms": self.reconnect_initial_delay_ms,
            "reconnect_max_delay_ms": self.reconnect_max_delay_ms,
            "reconnect_max_attempts": self.reconnect_max_attempts,
        }

    def to_redacted_json(self) -> str:
        return json.dumps(self.to_redacted_dict(), sort_keys=True, separators=(",", ":"))

    def __repr__(self) -> str:
        return "HAConfiguration(" + self.to_redacted_json() + ")"

    def __getstate__(self) -> NoReturn:
        raise TypeError("raw_configuration_serialization_forbidden")

    def __reduce__(self) -> NoReturn:
        raise TypeError("raw_configuration_serialization_forbidden")

    def __reduce_ex__(self, protocol: SupportsIndex) -> NoReturn:
        raise TypeError("raw_configuration_serialization_forbidden")
