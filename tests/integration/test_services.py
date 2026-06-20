"""REQ-002 服务类集成用例（env-gated；req_impl 起服务后转 passing）。

TC-002-03 OIDC / -06 Redis / -08 LiteLLM(key 隔离+三后端) / -09 Langfuse。
未设对应环境变量则 skip（见 tests/conftest.require）。
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

import pytest

from conftest import require


def _get_json(url: str):
    with urllib.request.urlopen(url, timeout=10) as r:  # noqa: S310 (内网/测试 URL)
        return json.loads(r.read())


_OIDC_CLIENT = "ai-family-chatui"
_OIDC_USERS = {"lin-dad": "admin", "lin-mom": "adult", "duoduo": "kid"}  # 代表性成员→角色
_OIDC_PASSWORD = "dev-pass-1234"


def _oidc_token(issuer: str, username: str) -> str:
    body = urllib.parse.urlencode({
        "grant_type": "password", "client_id": _OIDC_CLIENT,
        "username": username, "password": _OIDC_PASSWORD, "scope": "openid",
    }).encode()
    req = urllib.request.Request(
        issuer.rstrip("/") + "/protocol/openid-connect/token", data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310
        return json.loads(r.read())["access_token"]


# —— TC-002-03：IdP OIDC discovery ——
def test_oidc_discovery_exposes_endpoints():
    issuer = require("oidc")
    doc = _get_json(issuer.rstrip("/") + "/.well-known/openid-configuration")
    for key in ("authorization_endpoint", "token_endpoint", "jwks_uri", "issuer"):
        assert key in doc, f"OIDC discovery 缺 {key}"


# —— TC-002-03：JWT 签发 + JWKS 验签 + admin/adult/kid 三角色 claim ——
def test_oidc_jwt_issues_and_verifies_role_claims():
    issuer = require("oidc")
    jwt = pytest.importorskip("jwt")  # pyjwt[crypto]
    jwks = jwt.PyJWKClient(issuer.rstrip("/") + "/protocol/openid-connect/certs")
    seen_roles = set()
    for username, expected_role in _OIDC_USERS.items():
        token = _oidc_token(issuer, username)                 # 签发（password grant）
        key = jwks.get_signing_key_from_jwt(token).key
        claims = jwt.decode(token, key, algorithms=["RS256"], options={"verify_aud": False})  # 验签
        roles = claims.get("realm_access", {}).get("roles", [])
        assert expected_role in roles, f"{username} 缺角色 {expected_role}：{roles}"
        seen_roles.add(expected_role)
    assert seen_roles == {"admin", "adult", "kid"}, f"三角色未齐：{seen_roles}"


# —— TC-002-03：篡改 token 被拒 ——
def test_oidc_tampered_token_rejected():
    issuer = require("oidc")
    jwt = pytest.importorskip("jwt")
    token = _oidc_token(issuer, "duoduo")
    jwks = jwt.PyJWKClient(issuer.rstrip("/") + "/protocol/openid-connect/certs")
    key = jwks.get_signing_key_from_jwt(token).key
    tampered = token[:-4] + ("aaaa" if not token.endswith("aaaa") else "bbbb")
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(tampered, key, algorithms=["RS256"], options={"verify_aud": False})


# —— TC-002-06：Redis 会话缓存 ——
def test_redis_set_get_ttl():
    url = require("redis")
    redis = pytest.importorskip("redis")
    client = redis.Redis.from_url(url)
    client.set("aifam:test", "ok", ex=30)
    assert client.get("aifam:test") == b"ok"
    assert 0 < client.ttl("aifam:test") <= 30


# —— TC-002-08：LiteLLM 网关 ——
def test_litellm_key_isolation_and_backends():
    base = require("litellm").rstrip("/")
    # ① 无网关 key → 401/403（厂商 key 仅在网关，下游无 key 不可调用 —— BUG-003 隔离验证）
    with pytest.raises(urllib.error.HTTPError) as ei:
        urllib.request.urlopen(urllib.request.Request(base + "/v1/models"), timeout=10)  # noqa: S310
    assert ei.value.code in (401, 403), f"无 key 应被拒，实得 {ei.value.code}"
    # ② 带网关 key → 200 + 列出三后端档位
    key = os.getenv("AIFAMILY_LITELLM_KEY")
    if not key:
        pytest.skip("设 AIFAMILY_LITELLM_KEY 验证带 key 列模型")
    req = urllib.request.Request(base + "/v1/models", headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310
        ids = {m.get("id", "") for m in json.loads(r.read()).get("data", [])}
    assert {"deepseek-chat", "kimi", "claude"} <= ids, f"缺三后端档位，实得 {ids}"
    # TODO(req_impl): per-user 预算计数（master key + /key/generate per-user 虚拟 key）


# —— TC-002-09：Langfuse 可达 + trace 检索 ——
def test_langfuse_reachable():
    base = require("langfuse")
    # 健康检查；完整 trace 断言（token/cost/latency + trace_id 贯通）待 req_impl 接入 LiteLLM 出口
    with urllib.request.urlopen(base.rstrip("/") + "/api/public/health", timeout=10) as r:  # noqa: S310
        assert r.status == 200
    # TODO(req_impl): 发起一次经 LiteLLM 的调用 → 按 trace_id 检索 → 断言字段完整
