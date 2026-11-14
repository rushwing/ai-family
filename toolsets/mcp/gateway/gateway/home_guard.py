"""REQ-039 shared eligibility and registered entry. No task or provider dispatch.

Authority adapters are trusted server composition. Only a single, fenced store
is supported; PG authority writers must lock the same grant/generation rows.
Neither an exported verdict nor a caller-built context grants permission.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Literal, NoReturn, Protocol

import psycopg
from home_device_fabric.action_validation import ActionValidator
from home_device_fabric.ha_mapping import _json
from home_device_fabric.state_store import CurrentStateStore, StateView
from state_schema.action_contracts import ActionRequest, RequesterContext
from state_schema.capability import CapabilityDescriptor
from state_schema.home_inventory import CANONICAL_ID_PATTERN, Inventory
from state_schema.initial_capabilities import load_initial_capabilities
from state_schema.provider_binding import BindingCollection, ProviderBinding

from gateway.auth import AuthenticationError, AuthorizationError, verify_bearer
from gateway.tools import (
    HOME_ACTION_TOOL,
    AuthenticatedTool,
    ToolDenied,
    ToolUnavailable,
    gateway_registry,
)

_REJECTED = frozenset(
    {
        "unauthenticated",
        "session_required",
        "forbidden",
        "invalid_request",
        "input_too_large",
        "capabilities_uninitialized",
        "unknown_capability",
        "unsupported_capability_version",
        "read_only_capability",
        "unknown_action",
        "invalid_arguments",
        "unsupported_action",
        "device_unavailable",
    }
)
_GENERATION = re.compile(r"[A-Za-z0-9._:-]{1,128}", re.ASCII)
_ALLOWED = frozenset({("home.switchable", 1, "set_on"), ("home.positionable", 1, "set_position")})
Status = Literal["eligible", "rejected", "unavailable"]


@dataclass(frozen=True, slots=True, repr=False)
class GuardDecision:
    status: Status
    reason: str | None

    def __post_init__(self) -> None:
        valid = type(self.status) is str and (
            self.status == "eligible"
            and self.reason is None
            or self.status == "rejected"
            and type(self.reason) is str
            and self.reason in _REJECTED
            or self.status == "unavailable"
            and self.reason == "guard_unavailable"
        )
        if not valid:
            raise ValueError("invalid_guard_decision")

    def to_dict(self) -> dict[str, str | None]:
        return {"status": self.status, "reason": self.reason}

    def __repr__(self) -> str:
        return "GuardDecision()"

    def __reduce__(self) -> NoReturn:
        raise TypeError("guard_decision_serialization_forbidden")


def _reject(reason: str) -> GuardDecision:
    return GuardDecision("rejected", reason)


def _unavailable() -> GuardDecision:
    return GuardDecision("unavailable", "guard_unavailable")


class ScopeAuthority(Protocol):
    """Trusted adapter, never selected or supplied by the requesting principal."""

    coordination: str
    store: CurrentStateStore

    def lease(
        self,
        connection: psycopg.Connection,
        principal: dict[str, object],
        target: dict[str, object],
        timeout_seconds: int,
    ) -> AbstractContextManager[object]: ...


@dataclass(frozen=True, slots=True, init=False, repr=False)
class HomeActionGuard:
    _dsn: str
    _inventory: Inventory
    _bindings: tuple[tuple[str, str], ...]
    _validator: ActionValidator
    _initial: tuple[tuple[str, int, str], ...]
    _descriptors: tuple[tuple[str, str, int, str], ...]
    _generation: str
    _instance: str
    _authority: ScopeAuthority
    _store: CurrentStateStore
    _clock: Callable[[], int]
    _clock_lock: Lock
    _clock_values: list[int]
    _age: int
    _limit: int
    _wait: int

    def __init__(
        self,
        *,
        dsn: str,
        registered_inventory: object,
        bindings: object,
        capabilities: object,
        provider_instance_id: str,
        configuration_generation: str,
        authority: ScopeAuthority,
        store: CurrentStateStore,
        clock: Callable[[], int],
        max_availability_age_ms: int,
        max_input_bytes: int = 65536,
        scope_wait_seconds: int = 5,
    ) -> None:
        if hasattr(self, "_dsn"):
            raise AttributeError("immutable_home_guard")
        failed = False
        try:
            if (
                type(dsn) is not str
                or not dsn.strip()
                or type(store) is not CurrentStateStore
                or not callable(clock)
                or not callable(getattr(authority, "lease", None))
                or authority.coordination != "single_store_v1"
                or authority.store is not store
                or type(max_availability_age_ms) is not int
                or not 1 <= max_availability_age_ms <= 300000
                or type(scope_wait_seconds) is not int
                or not 1 <= scope_wait_seconds <= 5
                or type(configuration_generation) is not str
                or _GENERATION.fullmatch(configuration_generation) is None
                or type(provider_instance_id) is not str
                or CANONICAL_ID_PATTERN.fullmatch(provider_instance_id) is None
            ):
                raise ValueError
            inventory = Inventory.from_dict(json.loads(_json(registered_inventory)))
            bound = BindingCollection.from_dict(
                json.loads(_json(bindings)), inventory=inventory.to_dict()
            )
            if any(
                b.provider != "ha" or b.provider_instance_id != provider_instance_id
                for b in bound.bindings
            ):
                raise ValueError
            validator = ActionValidator(
                registered_inventory=inventory.to_dict(),
                capabilities=capabilities,
                max_input_bytes=max_input_bytes,
            )
            descriptors = tuple(
                (record["device_id"], d.capability_id, d.capability_version, _json(d.to_dict()))
                for record in json.loads(_json(capabilities))
                for d in (CapabilityDescriptor.from_dict(raw) for raw in record["capabilities"])
            )
            initial = tuple(
                (d.capability_id, d.capability_version, _json(d.to_dict()))
                for d in load_initial_capabilities().capabilities
            )
        except Exception:
            failed = True
        if failed:
            raise ValueError("invalid_guard_configuration")
        values = {
            "_dsn": dsn,
            "_inventory": inventory,
            "_bindings": tuple((b.device_id, _json(b.to_dict())) for b in bound.bindings),
            "_validator": validator,
            "_initial": initial,
            "_descriptors": descriptors,
            "_generation": configuration_generation,
            "_instance": provider_instance_id,
            "_authority": authority,
            "_store": store,
            "_clock": clock,
            "_clock_lock": Lock(),
            "_clock_values": [],
            "_age": max_availability_age_ms,
            "_limit": max_input_bytes,
            "_wait": scope_wait_seconds,
        }
        for name, value in values.items():
            object.__setattr__(self, name, value)

    def __repr__(self) -> str:
        return "HomeActionGuard()"

    def __reduce__(self) -> NoReturn:
        raise TypeError("home_guard_serialization_forbidden")

    @staticmethod
    def _identity(claims: dict[str, Any]) -> GuardDecision | None:
        if any(
            type(claims.get(k)) is not str or not claims[k].strip() or len(claims[k]) > 256
            for k in ("sub", "family_member_id")
        ):
            return _reject("unauthenticated")
        if claims.get("role") not in ("admin", "adult"):
            return _reject("forbidden")
        sid, state = claims.get("sid"), claims.get("session_state")
        if (
            sid is not None
            and (type(sid) is not str or not sid.strip() or len(sid) > 256)
            or state is not None
            and (type(state) is not str or not state.strip() or len(state) > 256)
            or sid is not None
            and state is not None
            and sid != state
            or sid is None
            and state is None
        ):
            return _reject("session_required")
        return None

    @contextmanager
    def _connection(self, member: str) -> Iterator[psycopg.Connection]:
        with psycopg.connect(self._dsn, connect_timeout=self._wait) as conn:
            conn.execute("SET LOCAL ROLE aifam_app")
            conn.execute("SET LOCAL search_path = public, pg_catalog")
            conn.execute("SELECT set_config('statement_timeout', %s, true)", (f"{self._wait}s",))
            conn.execute("SELECT set_config('lock_timeout', %s, true)", (f"{self._wait}s",))
            conn.execute("SELECT set_config('app.member_id', %s, true)", (member,))
            yield conn

    def _now(self) -> int:
        with self._clock_lock:
            value = self._clock()
            if (
                type(value) is not int
                or value < 0
                or self._clock_values
                and value < self._clock_values[0]
            ):
                raise ValueError("invalid_guard_clock")
            self._clock_values[:] = [value]
            return value

    def assess(self, bearer: str | None, request: object) -> GuardDecision:
        """Non-authorizing assessment. Original bearer required; never dispatches."""
        try:
            claims = verify_bearer(bearer)
        except AuthenticationError:
            return _reject("unauthenticated")
        except AuthorizationError:
            return _reject("forbidden")
        except Exception:
            return _unavailable()
        return self._preflight(claims, request)

    def _preflight(self, claims: dict[str, Any], request: object) -> GuardDecision:
        identity_error = self._identity(claims)
        if identity_error is not None:
            return identity_error
        # Parse/bound before opening authority DB; no descriptive lookup here.
        parsed = self._parse(request)
        if isinstance(parsed, GuardDecision):
            return parsed
        try:
            with self._connection(claims["family_member_id"]) as conn:
                with self._protected(claims, parsed, conn) as decision:
                    result = decision
            return result
        except Exception:
            return _unavailable()

    def _parse(self, request: object) -> ActionRequest | GuardDecision:
        try:
            encoded = _json(request)
            if len(encoded.encode("utf-8")) > self._limit:
                return _reject("input_too_large")
            return ActionRequest.from_dict(json.loads(encoded))
        except Exception:
            return _reject("invalid_request")

    @contextmanager
    def _protected(
        self, claims: dict[str, Any], request: ActionRequest, conn: psycopg.Connection
    ) -> Iterator[GuardDecision]:
        """Private trusted final seam. Yield only while DB+state protections live."""
        if (
            self._authority.coordination != "single_store_v1"
            or self._authority.store is not self._store
            or conn.execute("SELECT current_user, app_current_member()").fetchone()
            != ("aifam_app", claims["family_member_id"])
        ):
            raise ValueError("invalid_guard_scope")
        # AuthenticatedTool opens the final transaction; apply this guard's
        # configured resource-lock budget there as well as during preflight.
        conn.execute("SELECT set_config('lock_timeout', %s, true)", (f"{self._wait}s",))
        conn.execute("SELECT set_config('statement_timeout', %s, true)", (f"{self._wait}s",))
        principal = {
            "subject_id": claims["sub"],
            "family_member_id": claims["family_member_id"],
            "role": claims["role"],
        }
        target = request.identity.to_dict()
        expected_principal, expected_target = _json(principal), _json(target)
        with self._authority.lease(
            conn, json.loads(expected_principal), json.loads(expected_target), self._wait
        ) as raw:
            data = json.loads(_json(raw))
            if (
                type(data) is not dict
                or set(data) != {"principal", "target", "granted", "generation", "binding"}
                or _json(data["principal"]) != expected_principal
                or _json(data["target"]) != expected_target
                or type(data["granted"]) is not bool
            ):
                raise ValueError("invalid_guard_authority")
            if data["granted"] is False:
                yield _reject("forbidden")
                return
            home, device = request.identity.home_id, request.identity.device_id
            if (
                home != self._inventory.home.id
                or device not in {d.id for d in self._inventory.devices}
                or data["generation"] != self._generation
            ):
                yield _unavailable()
                return
            validated = self._validator.validate(request.to_dict())
            reason = validated.failure_code
            if reason is not None:
                yield (
                    _unavailable()
                    if reason in ("unknown_home", "unknown_device")
                    else _reject(reason)
                )
                return
            identity = request.identity
            if (
                identity.capability_id,
                identity.capability_version,
                identity.action_id,
            ) not in _ALLOWED:
                yield _reject("unsupported_action")
                return
            # REQ-037 accepts descriptors beyond the initial catalogue. This guard
            # only permits the unchanged initial write descriptors, not a forged schema.
            current = next(
                (
                    v
                    for dev, cap, version, v in self._descriptors
                    if (dev, cap, version)
                    == (device, identity.capability_id, identity.capability_version)
                ),
                None,
            )
            if (identity.capability_id, identity.capability_version, current) not in self._initial:
                yield _reject("unsupported_action")
                return
            expected = next((v for dev, v in self._bindings if dev == device), None)
            if data["binding"] is None or expected is None:
                yield _reject("device_unavailable")
                return
            binding = ProviderBinding.from_dict(data["binding"])
            if _json(binding.to_dict()) != expected:
                yield _unavailable()
                return
            context = RequesterContext.from_dict(principal | {"home_id": home}).to_dict()
            with self._store.capture_lease(
                context, home_id=home, device_id=device, timeout_seconds=self._wait
            ) as capture:
                if capture.version != 1 or capture.inventory.to_dict() != self._inventory.to_dict():
                    yield _unavailable()
                    return
                now = self._now()  # after both lock waits, never at preflight start
                # Signature/issuer/audience were verified at the external/tool
                # entry; a lock wait must not extend that access token's expiry.
                if float(claims["exp"]) <= time.time():
                    yield _reject("unauthenticated")
                    return
                view = capture.view(now_ms=now, max_age_ms=self._age)
                available = False
                if isinstance(view, StateView) and view.freshness == "fresh":
                    av = view.state.availability
                    if (
                        av.status == "online"
                        and av.observed_at is not None
                        and av.ordering is not None
                        and capture.epoch is not None
                        and av.ordering.epoch == capture.epoch
                    ):
                        observed = datetime.fromisoformat(av.observed_at.replace("Z", "+00:00"))
                        delta = observed - datetime(1970, 1, 1, tzinfo=timezone.utc)
                        micros = (delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds
                        available = 0 <= now * 1000 - micros <= self._age * 1000
                yield (
                    GuardDecision("eligible", None) if available else _reject("device_unavailable")
                )

    def as_tool(self) -> AuthenticatedTool:
        """Wire the shared gateway. No executor/task sink parameter exists."""
        return AuthenticatedTool(
            gateway_registry().get(HOME_ACTION_TOOL),
            dsn=self._dsn,
            policy=self._policy,
            handler=self._handler,
        )

    def _policy(self, claims: dict[str, Any], params: dict[str, Any]) -> bool:
        decision = self._preflight(claims, params)
        if decision.status == "unavailable":
            raise ToolUnavailable("tool_unavailable")
        return decision.status == "eligible"

    def _handler(
        self, claims: dict[str, Any], params: dict[str, Any], conn: psycopg.Connection
    ) -> dict[str, object]:
        identity_error = self._identity(claims)
        parsed = self._parse(params)
        if identity_error is not None or isinstance(parsed, GuardDecision):
            raise ToolDenied("forbidden")
        with self._protected(claims, parsed, conn) as decision:
            if decision.status == "rejected":
                raise ToolDenied("forbidden")
            if decision.status == "unavailable":
                raise ToolUnavailable("tool_unavailable")
            return self._disabled_entry()

    @staticmethod
    def _disabled_entry() -> dict[str, object]:
        # Retained inside both protections. Later governed task integration must
        # replace this under its own admission, never accept a cached verdict.
        raise ToolUnavailable("tool_unavailable")
