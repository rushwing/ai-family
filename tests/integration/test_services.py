"""REQ-002 服务类集成用例（env-gated；req_impl 起服务后转 passing）。

TC-002-03 OIDC / -06 Redis / -08 LiteLLM(key 隔离+三后端) / -09 Langfuse。
未设对应环境变量则 skip（见 tests/conftest.require）。
"""
import base64
import hashlib
import html
import http.cookiejar
import json
import os
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

import pytest

from conftest import require


def _get_json(url: str):
    with urllib.request.urlopen(url, timeout=10) as r:  # noqa: S310 (内网/测试 URL)
        return json.loads(r.read())


_OIDC_CLIENT = "ai-family-chatui"
_OIDC_AUD = "ai-family-chatui"
_OIDC_USERS = {"lin-dad": "admin", "lin-mom": "adult", "duoduo": "kid"}  # 代表性成员→角色
_OIDC_PASSWORD = "dev-pass-1234"
_OIDC_REDIRECT = "http://localhost:9999/callback"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):  # 不跟随 302，便于从 Location 取 code
        return None


def _oidc_code_pkce_token(issuer: str, username: str, password: str = _OIDC_PASSWORD) -> str:
    """完整 Authorization Code + PKCE(S256) 流程（模拟浏览器登录身份链）。"""
    issuer = issuer.rstrip("/")
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), _NoRedirect)
    # 1. authorize → 登录页
    authz = issuer + "/protocol/openid-connect/auth?" + urllib.parse.urlencode({
        "response_type": "code", "client_id": _OIDC_CLIENT, "redirect_uri": _OIDC_REDIRECT,
        "scope": "openid", "state": "st", "code_challenge": challenge, "code_challenge_method": "S256",
    })
    with opener.open(authz, timeout=10) as r:  # noqa: S310
        page = r.read().decode()
    action = html.unescape(re.search(r'action="([^"]+)"', page).group(1))
    # 2. 提交登录表单 → 302 携带 code（_NoRedirect 使其以 HTTPError(302) 抛出，从中取 Location）
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
    # 3. code + verifier 换 token
    tok = urllib.parse.urlencode({
        "grant_type": "authorization_code", "code": code, "redirect_uri": _OIDC_REDIRECT,
        "client_id": _OIDC_CLIENT, "code_verifier": verifier,
    }).encode()
    with urllib.request.urlopen(  # noqa: S310
        urllib.request.Request(issuer + "/protocol/openid-connect/token", data=tok,
                               headers={"Content-Type": "application/x-www-form-urlencoded"}), timeout=10) as r:
        return json.loads(r.read())["access_token"]


# —— TC-002-03：IdP OIDC discovery ——
def test_oidc_discovery_exposes_endpoints():
    issuer = require("oidc")
    doc = _get_json(issuer.rstrip("/") + "/.well-known/openid-configuration")
    for key in ("authorization_endpoint", "token_endpoint", "jwks_uri", "issuer"):
        assert key in doc, f"OIDC discovery 缺 {key}"


# —— TC-002-03：code+PKCE 登录 → JWKS 验签 + aud + admin/adult/kid 三角色 ——
def test_oidc_code_pkce_verifies_aud_and_roles():
    issuer = require("oidc")
    jwt = pytest.importorskip("jwt")  # pyjwt[crypto]
    jwks = jwt.PyJWKClient(issuer.rstrip("/") + "/protocol/openid-connect/certs")
    seen_roles = set()
    for username, expected_role in _OIDC_USERS.items():
        token = _oidc_code_pkce_token(issuer, username)           # code+PKCE 签发
        key = jwks.get_signing_key_from_jwt(token).key
        claims = jwt.decode(token, key, algorithms=["RS256"], audience=_OIDC_AUD)  # 验签 + aud + exp
        roles = claims.get("realm_access", {}).get("roles", [])
        assert expected_role in roles, f"{username} 缺角色 {expected_role}：{roles}"
        seen_roles.add(expected_role)
    assert seen_roles == {"admin", "adult", "kid"}, f"三角色未齐：{seen_roles}"


# —— TC-002-03：篡改 token 被拒 ——
def test_oidc_tampered_token_rejected():
    issuer = require("oidc")
    jwt = pytest.importorskip("jwt")
    token = _oidc_code_pkce_token(issuer, "duoduo")
    key = jwt.PyJWKClient(issuer.rstrip("/") + "/protocol/openid-connect/certs").get_signing_key_from_jwt(token).key
    tampered = token[:-4] + ("aaaa" if not token.endswith("aaaa") else "bbbb")
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(tampered, key, algorithms=["RS256"], audience=_OIDC_AUD)


# —— TC-002-03：过期 token 被拒（realm accessTokenLifespan=10s）——
def test_oidc_expired_token_rejected():
    issuer = require("oidc")
    jwt = pytest.importorskip("jwt")
    token = _oidc_code_pkce_token(issuer, "duoduo")
    key = jwt.PyJWKClient(issuer.rstrip("/") + "/protocol/openid-connect/certs").get_signing_key_from_jwt(token).key
    time.sleep(12)  # 超过 10s lifespan
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(token, key, algorithms=["RS256"], audience=_OIDC_AUD)


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


# —— TC-002-09：Langfuse 可达 ——
def test_langfuse_reachable():
    base = require("langfuse")
    with urllib.request.urlopen(base.rstrip("/") + "/api/public/health", timeout=10) as r:  # noqa: S310
        assert r.status == 200


# —— TC-002-09：一次 LiteLLM 调用 → 按唯一 trace_id 检索 Langfuse 完整 trace（token/成本/延迟）——
def test_langfuse_trace_complete():
    lf = require("langfuse").rstrip("/")
    litellm = require("litellm").rstrip("/")
    pk, sk = os.getenv("AIFAMILY_LANGFUSE_PK"), os.getenv("AIFAMILY_LANGFUSE_SK")
    key = os.getenv("AIFAMILY_LITELLM_KEY")
    if not (pk and sk and key):
        pytest.skip("设 AIFAMILY_LANGFUSE_PK/SK + AIFAMILY_LITELLM_KEY 验证完整 trace")
    trace_id = f"tc002-09-{uuid.uuid4()}"   # 唯一 id 关联本次调用（LiteLLM metadata.trace_id → Langfuse trace id）
    # ① 发起一次经 LiteLLM 的调用（mock 档位，无需厂商 key 即产出真实 token/cost）
    body = json.dumps({
        "model": "mock-test", "messages": [{"role": "user", "content": trace_id}],
        "metadata": {"trace_id": trace_id},
    }).encode()
    call = urllib.request.Request(
        litellm + "/v1/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(call, timeout=15) as r:  # noqa: S310
        assert r.status == 200
    # ② 按本次 trace_id 精确检索其 GENERATION（不取历史任意一条），断言 token/成本/延迟贯通
    auth = base64.b64encode(f"{pk}:{sk}".encode()).decode()
    for _ in range(12):
        time.sleep(1.5)
        q = urllib.request.Request(
            lf + f"/api/public/observations?traceId={trace_id}",
            headers={"Authorization": f"Basic {auth}"},
        )
        with urllib.request.urlopen(q, timeout=10) as r:  # noqa: S310
            obs = json.loads(r.read()).get("data", [])
        gens = [o for o in obs if o.get("type") == "GENERATION"]
        if gens:
            o = gens[0]
            assert o.get("traceId") == trace_id, "trace_id 未贯通到 observation"
            assert o.get("promptTokens") and o.get("completionTokens"), f"trace 缺 token：{o.get('usage')}"
            assert o.get("latency") is not None, "trace 缺 latency"
            assert o.get("calculatedTotalCost") is not None, "trace 缺 cost"
            return
    pytest.fail(f"未按 trace_id={trace_id} 检索到含 token/成本/延迟 的 GENERATION")
