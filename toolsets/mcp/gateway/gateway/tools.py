"""REQ-004 authenticated tool wrapper and fixed registered home boundary.

The wrapper checks JWT again at the tool, never trusts a body identity, and
runs the handler under transaction-local member RLS. The injected server policy
must check current device/home grants; canonical validation belongs to REQ-039.
No production Home handler or provider executor is supplied by this module.
"""

from __future__ import annotations

import copy
from collections.abc import Callable

import psycopg
from goal_mcp import Tool, ToolRegistry, tool_registry

from gateway.auth import AuthenticationError, AuthorizationError, verify_bearer

HOME_ACTION_TOOL = "home.execute_action"


def gateway_registry() -> ToolRegistry:
    registry = tool_registry()
    registry.register(
        Tool(
            HOME_ACTION_TOOL,
            "write",
            {
                "group": "home",
                "roles": frozenset({"admin", "adult"}),
                "tenant_scope": "member",
                "mutates": True,
                "auth": "oidc-jwt",
                "two_phase": True,
                "confirm_source": "user",
                "test_ref": "TC-004-02",
            },
        )
    )
    return registry


class ToolDenied(Exception):
    """Fixed denial without submitted identity, parameters or credentials."""


class ToolUnavailable(Exception):
    """Tool persistence or policy failed closed."""


class AuthenticatedTool:
    def __init__(
        self,
        spec: Tool,
        *,
        dsn: str,
        policy: Callable[[dict, dict], bool],
        handler: Callable[[dict, dict, psycopg.Connection], dict],
    ):
        # Snapshot and validate metadata; callers cannot mutate registration later.
        self._spec = Tool(spec.name, spec.risk, copy.deepcopy(spec.manifest))
        ToolRegistry().register(self._spec)
        if not dsn or not callable(policy) or not callable(handler):
            raise ValueError("tool database, policy and handler required")
        self._dsn, self._policy, self._handler = dsn, policy, handler

    def __repr__(self):
        return "<AuthenticatedTool>"

    def authorize(self, bearer: str | None, params: dict) -> dict:
        try:
            claims = verify_bearer(bearer)
        except (AuthenticationError, AuthorizationError):
            raise ToolDenied("forbidden") from None
        if claims["role"] not in self._spec.roles:
            raise ToolDenied("forbidden")
        member = params.get("family_member_id")
        if member is not None and member != claims["family_member_id"]:
            raise ToolDenied("forbidden")
        try:
            allowed = self._policy(copy.deepcopy(claims), copy.deepcopy(params))
        except Exception:
            raise ToolUnavailable("tool_unavailable") from None
        if allowed is not True:
            raise ToolDenied("forbidden")
        return claims

    def __call__(self, bearer: str | None, params: dict) -> dict:
        claims = self.authorize(bearer, params)
        try:
            with psycopg.connect(self._dsn, connect_timeout=5) as conn:
                conn.execute("SET LOCAL ROLE aifam_app")
                conn.execute("SET LOCAL search_path = public, pg_catalog")
                conn.execute("SET LOCAL statement_timeout = '5s'")
                conn.execute("SET LOCAL lock_timeout = '5s'")
                conn.execute(
                    "SELECT set_config('app.member_id', %s, true)", (claims["family_member_id"],)
                )
                # Mutable grants must be locked/rechecked by the trusted handler
                # on this connection before any write (see README).
                return self._handler(copy.deepcopy(claims), copy.deepcopy(params), conn)
        except ToolDenied:
            raise ToolDenied("forbidden") from None
        except ToolUnavailable:
            raise ToolUnavailable("tool_unavailable") from None
        except Exception:
            raise ToolUnavailable("tool_unavailable") from None

    @property
    def name(self) -> str:
        return self._spec.name
