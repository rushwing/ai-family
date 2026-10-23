"""Trusted scoped canonical reads; no provider operations or authentication (REQ-034)."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, NoReturn, TypeVar, cast

from state_schema.capability import CapabilityDescriptor
from state_schema.home_inventory import CANONICAL_ID_PATTERN, Inventory

from .ha_mapping import _json
from .state_store import CurrentStateStore, StateStoreError

__all__ = ["HomeQueryService", "HomeQueryError", "QueryResult"]

Status = Literal["found", "not_found", "uninitialized"]
T = TypeVar("T")
_CODES = frozenset(
    {
        "invalid_configuration",
        "invalid_context",
        "forbidden",
        "invalid_selector",
        "invalid_time",
        "clock_regression",
    }
)


class HomeQueryError(Exception):
    """Fixed diagnostics with no submitted values or retained underlying chains."""

    _code: str

    def __init__(self, code: str):
        if type(code) is not str or code not in _CODES:
            raise ValueError("invalid_diagnostic")
        if hasattr(self, "_code"):
            raise AttributeError("immutable_query_error")
        object.__setattr__(self, "_code", code)
        super().__init__(code)

    @property
    def code(self) -> str:
        return self._code

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code}

    def __str__(self) -> str:
        return self.code

    def __repr__(self) -> str:
        return f"HomeQueryError({self.code!r})"

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
        raise AttributeError("immutable_query_error")

    def __delattr__(self, name: str) -> NoReturn:
        raise AttributeError("immutable_query_error")

    def __reduce__(self) -> NoReturn:
        raise TypeError("query_error_serialization_forbidden")


def _read(function: Callable[[], T]) -> T:
    code = None
    try:
        return function()
    except StateStoreError as error:
        code = {
            "invalid_context": "invalid_context",
            "forbidden": "forbidden",
            "invalid_integer": "invalid_time",
            "invalid_identifier": "invalid_selector",
            "clock_regression": "clock_regression",
        }.get(error.code, "invalid_configuration")
    raise HomeQueryError(code)


def _id(value: object) -> str:
    if type(value) is not str or CANONICAL_ID_PATTERN.fullmatch(value) is None:
        raise HomeQueryError("invalid_selector")
    return value


@dataclass(frozen=True, slots=True, repr=False, init=False)
class QueryResult:
    """Immutable bounded plain-JSON result; serialize only at an authorized boundary.

    Direct construction validates data with the same limits as configuration.
    Invalid data raises a redacted HomeQueryError(invalid_configuration).
    """

    _payload: str

    def __init__(self, status: Status, data: object):
        if hasattr(self, "_payload"):
            raise AttributeError("immutable_query_result")
        if type(status) is not str or status not in ("found", "not_found", "uninitialized"):
            raise ValueError("invalid_result_status")
        failed = False
        payload = ""
        try:
            payload = _json({"status": status, "data": data})
        except Exception:
            failed = True
        if failed:
            raise HomeQueryError("invalid_configuration")
        object.__setattr__(self, "_payload", payload)

    @property
    def status(self) -> Status:
        return cast(Status, self.to_dict()["status"])

    def to_dict(self) -> dict[str, object]:
        return cast(dict[str, object], json.loads(self._payload))

    def __repr__(self) -> str:
        return "QueryResult(<redacted>)"

    def __reduce__(self) -> NoReturn:
        raise TypeError("query_result_serialization_forbidden")


@dataclass(frozen=True, slots=True, repr=False, init=False)
class HomeQueryService:
    """Read-only service over one fixed store and a fixed canonical descriptor snapshot.

    Requester contexts and store grants must originate in trusted composition.
    Neither this class nor CurrentStateStore verifies an authentication token.
    """

    _store: CurrentStateStore
    _capabilities: tuple[tuple[str, str, str], ...]

    def __init__(self, *, store: object, capabilities: object):
        if hasattr(self, "_store"):
            raise AttributeError("immutable_query_service")
        failed = False
        records: list[tuple[str, str, str]] = []
        try:
            if type(store) is not CurrentStateStore:
                raise ValueError()
            raw = json.loads(_json(capabilities))
            if type(raw) is not list:
                raise ValueError()
            keys: set[tuple[str, str]] = set()
            for record in raw:
                if type(record) is not dict or set(record) != {
                    "home_id",
                    "device_id",
                    "capabilities",
                }:
                    raise ValueError()
                home, device = _id(record["home_id"]), _id(record["device_id"])
                if (home, device) in keys or type(record["capabilities"]) is not list:
                    raise ValueError()
                keys.add((home, device))
                descriptors = [
                    CapabilityDescriptor.from_dict(item) for item in record["capabilities"]
                ]
                pairs = {(item.capability_id, item.capability_version) for item in descriptors}
                if len(pairs) != len(descriptors):
                    raise ValueError()
                descriptors.sort(key=lambda item: (item.capability_id, item.capability_version))
                records.append((home, device, json.dumps([item.to_dict() for item in descriptors])))
        except Exception:
            failed = True
        if failed:
            raise HomeQueryError("invalid_configuration")
        object.__setattr__(self, "_store", store)
        object.__setattr__(self, "_capabilities", tuple(sorted(records)))

    def __repr__(self) -> str:
        return "HomeQueryService(<redacted>)"

    def __reduce__(self) -> NoReturn:
        raise TypeError("query_service_serialization_forbidden")

    def _inventory(self, context: object, home_id: object) -> Inventory:
        return _read(lambda: self._store.inventory(context, home_id=home_id))

    def home(self, context: object, *, home_id: object) -> QueryResult:
        inventory = self._inventory(context, home_id)
        return QueryResult("found", inventory.to_dict()["home"])

    def areas(self, context: object, *, home_id: object) -> QueryResult:
        inventory = self._inventory(context, home_id)
        rows = cast(list[dict[str, object]], inventory.to_dict()["areas"])
        return QueryResult("found", sorted(rows, key=lambda row: cast(str, row["id"])))

    def devices(
        self,
        context: object,
        *,
        home_id: object,
        area_id: object = None,
    ) -> QueryResult:
        inventory = self._inventory(context, home_id)
        if area_id is not None:
            area = _id(area_id)
            if not any(item.id == area for item in inventory.areas):
                return QueryResult("not_found", None)
        rows = cast(list[dict[str, object]], inventory.to_dict()["devices"])
        selected = [row for row in rows if area_id is None or row["area_id"] == area_id]
        return QueryResult("found", sorted(selected, key=lambda row: cast(str, row["id"])))

    def device(self, context: object, *, home_id: object, device_id: object) -> QueryResult:
        inventory = self._inventory(context, home_id)
        device = _id(device_id)
        rows = cast(list[dict[str, object]], inventory.to_dict()["devices"])
        row = next((item for item in rows if item["id"] == device), None)
        return QueryResult("not_found" if row is None else "found", row)

    def states(
        self,
        context: object,
        *,
        home_id: object,
        now_ms: object,
        max_age_ms: object,
    ) -> QueryResult:
        views = _read(
            lambda: self._store.snapshot(
                context,
                home_id=home_id,
                now_ms=now_ms,
                max_age_ms=max_age_ms,
            )
        )
        return QueryResult("found", [view.to_dict() for view in views])

    def state(
        self,
        context: object,
        *,
        home_id: object,
        device_id: object,
        now_ms: object,
        max_age_ms: object,
    ) -> QueryResult:
        self._inventory(context, home_id)
        device = _id(device_id)
        view = _read(
            lambda: self._store.read(
                context,
                home_id=home_id,
                device_id=device,
                now_ms=now_ms,
                max_age_ms=max_age_ms,
            )
        )
        if view.to_dict()["status"] == "not_found":
            return QueryResult("not_found", None)
        return QueryResult("found", view.to_dict())

    def capabilities(
        self,
        context: object,
        *,
        home_id: object,
        device_id: object,
    ) -> QueryResult:
        inventory = self._inventory(context, home_id)
        device = _id(device_id)
        if not any(item.id == device for item in inventory.devices):
            return QueryResult("not_found", None)
        for home, candidate, payload in self._capabilities:
            if home == inventory.home.id and candidate == device:
                return QueryResult("found", json.loads(payload))
        return QueryResult("uninitialized", None)
