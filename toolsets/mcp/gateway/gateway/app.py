"""MCP 网关（信任边界）—— REQ-003 WP-4 / TC-003-04（B）·TC-003-02（B）。

所有 GoalAgent 工具调用的唯一入口 /tools/{tool}：
  ① 工具侧 OIDC JWT 验签（缺/非 JWT/篡改 → 401；旧 X-Telegram header 非 JWT → 401）
  ② manifest 角色门禁（kid 不得写 create/approve 等 → 403）
  ③ tenant scope：body 显式 family_member_id ≠ 调用者 → 跨成员越权 403 + 审计
  ④ write 类两段式：独立 ChatUI/BFF 交互证明才可签发 confirm token；execute 须带
     网关签发、会话+成员+工具+payload 绑定、一次性 token，普通 Agent bearer 不能自确认
  ⑤ 旧 REST / OpenClaw 直连禁用（410）
  ⑥ deny/allow 均落审计，/audit/recent 可查

角色 / scope / risk 来自 goal_mcp 的 manifest 契约（单一真值），网关不另立策略。
工具的**功能分发**经 executor 注入；未配置 executor 时 fail-closed（503），绝不伪造成功。
真实分发到 goal-mcp FastMCP 随服务联调在 req_impl_review 闭环。
"""
from __future__ import annotations

import inspect
import os
import time
from collections import deque
from typing import Any, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from goal_mcp import tool_registry
from starlette.concurrency import run_in_threadpool

from gateway.auth import AuthenticationError, AuthorizationError, verify_bearer
from gateway.confirm import ConfirmStore, confirmation_payload
from gateway.interaction import InteractionProofError, InteractionVerifier

ToolExecutor = Callable[[str, str, dict], dict]


def create_app(
    executor: ToolExecutor | None = None,
    *,
    confirmation_secret: str | None = None,
) -> FastAPI:
    app = FastAPI(title="ai-family MCP Gateway", version="0.1.0")
    registry = tool_registry()
    tools = {t.name: t for t in registry.list_tools()}
    confirm = ConfirmStore()
    interaction = InteractionVerifier(
        confirmation_secret
        if confirmation_secret is not None
        else os.getenv("AIFAMILY_CONFIRMATION_SECRET", "")
    )
    # Temporary WP-4 boundary buffer.  Durable audit.event integration remains
    # a req_impl_review task, but the interim process must still be bounded.
    audit: deque[dict[str, Any]] = deque(maxlen=1_000)

    def _record(action: str, result: str, member: str | None, reason: str = "") -> None:
        audit.append(
            {
                # Audit attacker-controlled path text, never credentials/body;
                # cap fields to keep denial telemetry safe and bounded.
                "action": action[:128],
                "result": result,
                "member": member,
                "reason": reason[:128],
                "ts": time.time(),
            }
        )

    def _bearer(request: Request) -> str | None:
        h = request.headers.get("authorization", "")
        if h.lower().startswith("bearer "):
            return h[7:].strip()
        return None  # 含旧 X-Telegram-Chat-Id 但无 Bearer → 视为缺 token

    def _session(claims: dict) -> str | None:
        value = claims.get("sid") or claims.get("session_state")
        return value if isinstance(value, str) and value.strip() else None

    @app.post("/tools/{tool}")
    async def call_tool(tool: str, request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            _record(tool, "deny", None, "invalid_json")
            return JSONResponse({"error": "invalid_json"}, status_code=400)
        if not isinstance(body, dict):
            _record(tool, "deny", None, "invalid_body")
            return JSONResponse({"error": "invalid_body"}, status_code=422)

        # ① 身份可信
        try:
            claims = verify_bearer(_bearer(request))
        except AuthenticationError:
            _record(tool, "deny", None, "unauthenticated")
            return JSONResponse({"error": "unauthenticated"}, status_code=401)
        except AuthorizationError:
            _record(tool, "deny", None, "unrecognized_role")
            return JSONResponse({"error": "forbidden"}, status_code=403)
        member = claims["family_member_id"]

        # 未知 tool
        spec = tools.get(tool)
        if spec is None:
            _record(tool, "deny", member, "unknown_tool")
            return JSONResponse({"error": "unknown_tool"}, status_code=404)

        # ③ tenant scope：显式跨成员参数 → 越权
        req_member = body.get("family_member_id")
        if req_member is not None and str(req_member) != str(member):
            _record(tool, "deny", member, "cross_member_param")
            return JSONResponse({"error": "cross_member"}, status_code=403)

        # ② 角色门禁
        if claims["role"] not in spec.roles:
            _record(tool, "deny", member, f"role_{claims['role']}_not_allowed")
            return JSONResponse({"error": "role_forbidden"}, status_code=403)

        # No runtime dispatcher means this process is a boundary-only build.
        # Reject both reads and write prepares before issuing confirmation state.
        if executor is None:
            _record(tool, "deny", member, "executor_unavailable")
            return JSONResponse({"error": "executor_unavailable"}, status_code=503)

        # ④ write 类两段式
        if spec.risk == "write":
            if body.get("prepare") is True:
                _record(tool, "deny", member, "ordinary_channel_cannot_confirm")
                return JSONResponse({"error": "use_user_confirmation_channel"}, status_code=403)
            session = _session(claims)
            if session is None:
                _record(tool, "deny", member, "missing_session")
                return JSONResponse({"error": "session_required"}, status_code=401)
            ok = confirm.consume(
                body.get("confirm_token"),
                member=member,
                session=session,
                tool=tool,
                params=body,
            )
            if not ok:
                _record(tool, "deny", member, "bad_confirm_token")
                return JSONResponse({"error": "confirm_required"}, status_code=400)

        params = confirmation_payload(body)
        try:
            if inspect.iscoroutinefunction(executor):
                result = await executor(tool, member, params)
            else:
                result = await run_in_threadpool(executor, tool, member, params)
                if inspect.isawaitable(result):
                    result = await result
        except Exception:
            _record(tool, "deny", member, "executor_failed")
            return JSONResponse({"error": "executor_failed"}, status_code=502)
        _record(tool, "allow", member, "execute")
        return JSONResponse({"ok": True, "result": result}, status_code=200)

    @app.post("/confirmations/{tool}")
    async def create_confirmation(tool: str, request: Request) -> JSONResponse:
        """Mint a token only from the independently authenticated ChatUI/BFF channel."""
        try:
            body = await request.json()
        except Exception:
            _record(tool, "deny", None, "invalid_confirmation_json")
            return JSONResponse({"error": "invalid_json"}, status_code=400)
        if not isinstance(body, dict):
            _record(tool, "deny", None, "invalid_confirmation_body")
            return JSONResponse({"error": "invalid_body"}, status_code=422)
        try:
            claims = verify_bearer(_bearer(request))
        except (AuthenticationError, AuthorizationError):
            _record(tool, "deny", None, "confirmation_unauthenticated")
            return JSONResponse({"error": "unauthenticated"}, status_code=401)
        member = claims["family_member_id"]
        spec = tools.get(tool)
        if spec is None:
            _record(tool, "deny", member, "unknown_tool")
            return JSONResponse({"error": "unknown_tool"}, status_code=404)
        if spec.risk != "write" or claims["role"] not in spec.roles:
            _record(tool, "deny", member, "confirmation_forbidden")
            return JSONResponse({"error": "forbidden"}, status_code=403)
        req_member = body.get("family_member_id")
        if req_member is not None and str(req_member) != str(member):
            _record(tool, "deny", member, "cross_member_param")
            return JSONResponse({"error": "cross_member"}, status_code=403)
        session = _session(claims)
        if session is None:
            _record(tool, "deny", member, "missing_session")
            return JSONResponse({"error": "session_required"}, status_code=401)
        if executor is None:
            _record(tool, "deny", member, "executor_unavailable")
            return JSONResponse({"error": "executor_unavailable"}, status_code=503)
        try:
            interaction.verify(
                timestamp=request.headers.get("x-ai-family-interaction-timestamp"),
                nonce=request.headers.get("x-ai-family-interaction-nonce"),
                signature=request.headers.get("x-ai-family-interaction-signature"),
                session=session,
                member=member,
                tool=tool,
                params=body,
            )
        except InteractionProofError:
            _record(tool, "deny", member, "invalid_user_interaction_proof")
            return JSONResponse({"error": "user_confirmation_required"}, status_code=403)
        token = confirm.issue(
            member=member,
            session=session,
            tool=tool,
            params=body,
        )
        _record(tool, "allow", member, "user_confirmed")
        return JSONResponse({"confirm_token": token}, status_code=200)

    @app.get("/audit/recent")
    async def audit_recent(request: Request) -> JSONResponse:
        try:
            claims = verify_bearer(_bearer(request))
        except (AuthenticationError, AuthorizationError):
            return JSONResponse({"error": "unauthenticated"}, status_code=401)
        action = request.query_params.get("action")
        result = request.query_params.get("result")
        rows = [
            r
            for r in audit
            if (action is None or r["action"] == action)
            and (result is None or r["result"] == result)
            and (claims["role"] == "admin" or r["member"] == claims["family_member_id"])
        ]
        return JSONResponse(rows, status_code=200)

    # ⑤ 旧 REST / OpenClaw 直连禁用（M1 只走网关 /tools/*）
    @app.api_route("/api/v1/{rest:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def legacy_rest(rest: str) -> JSONResponse:
        return JSONResponse({"error": "legacy_rest_disabled"}, status_code=410)

    @app.api_route("/openclaw/{rest:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def legacy_openclaw(rest: str) -> JSONResponse:
        return JSONResponse({"error": "openclaw_disabled"}, status_code=410)

    @app.get("/healthz")
    async def healthz() -> dict:
        return {
            "status": "ok",
            "tools": len(tools),
            "issuer": bool(os.getenv("AIFAMILY_OIDC_ISSUER")),
            "executor_configured": executor is not None,
            "confirmation_channel_configured": interaction.configured,
        }

    @app.get("/readyz")
    async def readyz() -> JSONResponse:
        missing = []
        if executor is None:
            missing.append("executor")
        if not interaction.configured:
            missing.append("confirmation_channel")
        if missing:
            return JSONResponse({"status": "not_ready", "missing": missing}, 503)
        return JSONResponse({"status": "ready"}, 200)

    return app


app = create_app()
