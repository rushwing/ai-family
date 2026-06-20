"""共享 OIDC 登录 helper —— 完整 Authorization Code + PKCE(S256) 流程（纯 stdlib）。

BUG-031 修复：统一命名 `login_code_pkce`（此前网关测试拼成 login_code_pkke 且模块缺失）。
被 REQ-003 的网关/agent 集成测试复用，避免各处重复实现登录链。

实现承自 REQ-002 tests/integration/test_services.py 的 _oidc_login（模拟浏览器登录身份链）。
"""
from __future__ import annotations

import base64
import hashlib
import html
import http.cookiejar
import json
import os
import re
import secrets
import urllib.error
import urllib.parse
import urllib.request

CLIENT = os.getenv("AIFAMILY_OIDC_CLIENT", "ai-family-chatui")
REDIRECT = os.getenv("AIFAMILY_OIDC_REDIRECT", "http://localhost:9999/callback")
PASSWORD = os.getenv("AIFAMILY_OIDC_PASSWORD", "dev-pass-1234")

# 角色 → realm 用户名（与 REQ-002 realm 一致）。best_pal→admin / go_getter→adult·kid。
ROLE_USERS = {"admin": "lin-dad", "adult": "lin-mom", "kid": "duoduo"}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):  # 不跟随 302，便于从 Location 取 code
        return None


def login_code_pkce(issuer: str, username: str, password: str = PASSWORD) -> str:
    """以 code+PKCE 登录，返回 access_token（字符串）。失败抛异常（不静默 skip）。"""
    return login_tokens(issuer, username, password)["access_token"]


def login_role(issuer: str, role: str, password: str = PASSWORD) -> str:
    """按角色（admin/adult/kid）登录，便于测试不关心具体 realm 用户名。"""
    return login_code_pkce(issuer, ROLE_USERS[role], password)


def login_tokens(issuer: str, username: str, password: str = PASSWORD) -> dict:
    """完整 code+PKCE 流程，返回 token 响应（access_token + id_token）。"""
    issuer = issuer.rstrip("/")
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), _NoRedirect)
    authz = issuer + "/protocol/openid-connect/auth?" + urllib.parse.urlencode({
        "response_type": "code", "client_id": CLIENT, "redirect_uri": REDIRECT,
        "scope": "openid", "state": "st",
        "code_challenge": challenge, "code_challenge_method": "S256",
    })
    with opener.open(authz, timeout=10) as r:  # noqa: S310
        page = r.read().decode()
    action = html.unescape(re.search(r'action="([^"]+)"', page).group(1))
    data = urllib.parse.urlencode({"username": username, "password": password}).encode()
    login_req = urllib.request.Request(
        action, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        resp = opener.open(login_req, timeout=10)  # noqa: S310
        loc, status = resp.headers.get("Location"), resp.status
    except urllib.error.HTTPError as e:
        loc, status = e.headers.get("Location"), e.code
    assert loc, f"登录未返回重定向（凭证错误？）：{status}"
    code = urllib.parse.parse_qs(urllib.parse.urlparse(loc).query)["code"][0]
    tok = urllib.parse.urlencode({
        "grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT,
        "client_id": CLIENT, "code_verifier": verifier,
    }).encode()
    with urllib.request.urlopen(  # noqa: S310
        urllib.request.Request(
            issuer + "/protocol/openid-connect/token", data=tok,
            headers={"Content-Type": "application/x-www-form-urlencoded"}), timeout=10) as r:
        return json.loads(r.read())
