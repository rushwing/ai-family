"""网关侧 OIDC JWT 验签 —— REQ-003 WP-4 / TC-003-02（B）·TC-003-04（B）。

网关是信任边界：所有 /tools/* 调用在此校验 OIDC access token（JWKS 验签 + aud + exp +
issuer），从 JWT 取 role / sub / family_member_id。角色 / tenant 策略由 goal_mcp 的 manifest
契约统一供给（单一真值），本模块只负责「身份可信」与「role/member 取值」。

旧 X-Telegram-Chat-Id header 非 JWT → 一律 AuthenticationError（退役旧鉴权，BUG-017）。

env：AIFAMILY_OIDC_ISSUER（如 http://idp/realms/ai-family）、AIFAMILY_OIDC_AUD（默认 ai-family-chatui）。

注：libs/auth 契约就绪后（后续 REQ）网关与 agent 侧应共用同一 verifier；M1 各自内建。
"""
from __future__ import annotations

import os

import jwt  # PyJWT[crypto]


class AuthenticationError(Exception):
    """token 缺失 / 非 JWT（旧 header）/ 过期 / 篡改 / aud·iss 不符——身份不可信。"""


class AuthorizationError(Exception):
    """身份可信但无权（角色不允许 / 跨成员越权）。"""


def _issuer() -> str:
    return os.environ.get("AIFAMILY_OIDC_ISSUER", "").rstrip("/")


def _aud() -> str:
    return os.getenv("AIFAMILY_OIDC_AUD", "ai-family-chatui")


_PLATFORM_ROLES = {"admin", "adult", "kid"}
_ROLE_MAP = {"best_pal": "admin", "go_getter": "adult"}  # 旧名兜底；kid 由 realm 显式签发

_jwks_clients: dict[str, "jwt.PyJWKClient"] = {}


def _jwks(issuer: str) -> "jwt.PyJWKClient":
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


def verify_bearer(token: str | None) -> dict:
    """JWKS 验签 + aud + exp + issuer，返回含 role / sub / family_member_id 的 claims。

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
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=_aud(),
            issuer=issuer,
            options={"require": ["exp", "sub", "aud", "iss"]},
        )
    except Exception as e:  # PyJWKClientError / DecodeError / ExpiredSignatureError / Invalid*…
        raise AuthenticationError(f"token 不可信：{type(e).__name__}: {e}") from e

    role = _map_role(claims)  # 角色不可识别 → AuthorizationError
    member = (
        claims.get("family_member_id")
        or claims.get("preferred_username")
        or claims.get("sub")
    )
    return {**claims, "role": role, "family_member_id": member}
