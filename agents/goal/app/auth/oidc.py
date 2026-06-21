"""工具侧 OIDC JWT 鉴权 —— REQ-003 WP-2 / TC-003-02（需求 2 / 验收 #1）。

替换 goal-agent 旧的 X-Telegram-Chat-Id header 鉴权：MCP 工具在自身入口校验 OIDC access
token（JWKS 验签 + aud + exp + issuer），从验证后的 JWT 取 role / sub / family_member_id，
再按逐 tool 策略（角色 + tenant scope）授权。

角色映射：best_pal→admin / go_getter→adult·kid（realm 直接签发 admin/adult/kid 时原样）。
工具策略与 toolsets/mcp/goal-mcp 的 manifest 契约一致（test_goal_manifest EXPECTED）。

env：AIFAMILY_OIDC_ISSUER（如 http://idp/realms/ai-family）、AIFAMILY_OIDC_AUD（默认 ai-family-chatui）。
"""
from __future__ import annotations

import os
import time

import jwt  # PyJWT[crypto]


class AuthenticationError(Exception):
    """token 缺失 / 过期 / 篡改 / 非 JWT（旧 header）等——身份不可信。"""


class AuthorizationError(Exception):
    """身份可信但无权：角色不允许该 tool，或跨成员越权。"""


def _issuer() -> str:
    return os.environ.get("AIFAMILY_OIDC_ISSUER", "").rstrip("/")


_AUD = os.getenv("AIFAMILY_OIDC_AUD", "ai-family-chatui")
_PLATFORM_ROLES = {"admin", "adult", "kid"}
_ROLE_MAP = {"best_pal": "admin", "go_getter": "adult"}  # 旧名兜底；kid 由 realm 显式签发

# —— 逐 tool 策略：tool -> (allowed_roles, scope)；与 manifest 契约一致 ——
_ADMIN = frozenset({"admin"})
_W = frozenset({"admin", "adult"})          # 写：家长 + 成人
_R = frozenset({"admin", "adult", "kid"})   # 读 / 打卡：含 kid（只读自有 + Draft-First）
_M, _S = "member", "shared"

TOOL_POLICY: dict[str, tuple[frozenset, str]] = {
    # admin_tools（成员管理，仅 admin，平台/共享 scope）
    "add_go_getter": (_ADMIN, _S), "update_go_getter": (_ADMIN, _S),
    "remove_go_getter": (_ADMIN, _S), "list_go_getters": (_ADMIN, _S),
    "add_best_pal": (_ADMIN, _S), "update_best_pal": (_ADMIN, _S),
    "remove_best_pal": (_ADMIN, _S), "list_best_pals": (_ADMIN, _S),
    # checkin（读全角色；写含 kid 的 Draft-First 打卡）
    "list_today_tasks": (_R, _M), "list_week_tasks": (_R, _M),
    "checkin_task": (_R, _M), "skip_task": (_R, _M), "get_go_getter_progress": (_R, _M),
    # plan（写 admin+adult；读全角色，kid 只读自有由 member scope + RLS 保证）
    "create_target": (_W, _M), "update_target": (_W, _M), "delete_target": (_W, _M),
    "list_targets": (_R, _M), "generate_plan": (_W, _M), "update_plan": (_W, _M),
    "cancel_plan": (_W, _M), "list_plans": (_R, _M), "get_plan_detail": (_R, _M),
    # report（写 admin+adult；读全角色）
    "generate_daily_report": (_W, _M), "generate_weekly_report": (_W, _M),
    "generate_monthly_report": (_W, _M), "list_reports": (_R, _M),
    # tracks（目录，读，全角色，共享）
    "list_track_categories": (_R, _S), "list_track_subcategories": (_R, _S),
    # wizard（写 admin+adult）
    "start_goal_group_wizard": (_W, _M), "get_wizard_status": (_R, _M),
    "set_wizard_scope": (_W, _M), "set_wizard_targets": (_W, _M),
    "set_wizard_constraints": (_W, _M), "adjust_wizard": (_W, _M),
    "confirm_goal_group": (_W, _M), "cancel_goal_group_wizard": (_W, _M),
}

# JWKS 客户端按 issuer 缓存（避免每次 verify 重新拉取；realm token 仅 10s 有效，需快）
_jwks_clients: dict[str, jwt.PyJWKClient] = {}


def _jwks(issuer: str) -> jwt.PyJWKClient:
    client = _jwks_clients.get(issuer)
    if client is None:
        client = jwt.PyJWKClient(issuer + "/protocol/openid-connect/certs")
        _jwks_clients[issuer] = client
    return client


def _map_role(claims: dict) -> str:
    roles = set(claims.get("realm_access", {}).get("roles", []))
    raw = claims.get("role")
    if raw:
        roles.add(raw)
    for r in roles:
        if r in _PLATFORM_ROLES:
            return r
        if r in _ROLE_MAP:
            return _ROLE_MAP[r]
    raise AuthorizationError(f"无可识别角色：{sorted(roles)}")


def verify_access_token(token: str | None) -> dict:
    """JWKS 验签 + aud + exp + issuer；返回含 role / sub / family_member_id 的 claims。

    任何身份不可信情形（缺失 / 非 JWT / 过期 / 篡改 / aud·iss 不符）→ AuthenticationError。
    """
    if not token:
        raise AuthenticationError("缺少 access token")
    issuer = _issuer()
    if not issuer:
        raise AuthenticationError("未配置 AIFAMILY_OIDC_ISSUER")
    try:
        signing_key = _jwks(issuer).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token, signing_key.key, algorithms=["RS256"],
            audience=_AUD, issuer=issuer,
            options={"require": ["exp", "sub", "aud", "iss"]},
        )
    except AuthenticationError:
        raise
    except Exception as e:  # PyJWKClientError / DecodeError / ExpiredSignatureError / Invalid* …
        raise AuthenticationError(f"token 不可信：{type(e).__name__}: {e}") from e

    role = _map_role(claims)  # 可能抛 AuthorizationError（角色不可识别）
    # 平台无 family_member_id 自定义 claim 时，从 preferred_username / sub 派生（稳定且每成员互异）
    member = claims.get("family_member_id") or claims.get("preferred_username") or claims.get("sub")
    return {**claims, "role": role, "family_member_id": member}


def authorize_tool(token: str | None, tool: str, *, member: str | None = None) -> bool:
    """工具侧授权：验签身份 → 校验角色允许该 tool → 校验 member scope（防跨成员越权）。

    通过返回 True；身份不可信 → AuthenticationError；无权 / 越权 → AuthorizationError。
    """
    claims = verify_access_token(token)  # AuthenticationError 冒泡
    policy = TOOL_POLICY.get(tool)
    if policy is None:
        raise AuthorizationError(f"未知 tool：{tool}")
    roles, scope = policy
    if claims["role"] not in roles:
        raise AuthorizationError(
            f"角色 {claims['role']} 无权调用 {tool}（需 {sorted(roles)}）"
        )
    if scope == _M:
        # member-scoped 工具必须显式给出目标成员；缺失即 fail-closed（防调用方遗漏 tenant scope 绕过）
        if member is None:
            raise AuthorizationError(f"{tool} 为 member-scoped，必须显式传 member（fail-closed）")
        if member != claims["family_member_id"]:
            raise AuthorizationError(
                f"跨成员越权：claim={claims['family_member_id']} 请求 member={member}"
            )
    return True


def sample_bad_token(kind: str) -> str:
    """生成各类不可信 token，供 TC 验证 AuthenticationError（missing/expired/tampered/legacy_header）。"""
    if kind == "missing":
        return ""
    if kind == "legacy_header":
        return "X-Telegram-Chat-Id 123456"  # 旧 header 鉴权——非 JWT
    # expired / tampered：结构像 JWT 但无法用 realm JWKS 验签（无匹配 kid / 签名不符）→ 验签失败
    payload = {"sub": "x", "aud": _AUD, "iss": _issuer(), "realm_access": {"roles": ["kid"]}}
    if kind == "expired":
        payload["exp"] = int(time.time()) - 60
    else:  # tampered
        payload["exp"] = int(time.time()) + 600
    return jwt.encode(payload, "not-the-realm-key-" + "0" * 32, algorithm="HS256",
                      headers={"kid": "bogus"})
