"""REQ-002 服务类集成用例（env-gated；req_impl 起服务后转 passing）。

TC-002-03 OIDC / -06 Redis / -08 LiteLLM / -09 Langfuse。
未设对应环境变量则 skip（见 tests/conftest.require）。
"""
import json
import urllib.request

import pytest

from conftest import require


def _get_json(url: str):
    with urllib.request.urlopen(url, timeout=10) as r:  # noqa: S310 (内网/测试 URL)
        return json.loads(r.read())


# —— TC-002-03：IdP OIDC discovery ——
def test_oidc_discovery_exposes_endpoints():
    issuer = require("oidc")
    doc = _get_json(issuer.rstrip("/") + "/.well-known/openid-configuration")
    for key in ("authorization_endpoint", "token_endpoint", "jwks_uri", "issuer"):
        assert key in doc, f"OIDC discovery 缺 {key}"
    # TODO(req_impl): code+PKCE 取 token、校验 4 成员 / admin·adult·kid 角色 claim、过期/篡改拒绝


# —— TC-002-06：Redis 会话缓存 ——
def test_redis_set_get_ttl():
    url = require("redis")
    redis = pytest.importorskip("redis")
    client = redis.Redis.from_url(url)
    client.set("aifam:test", "ok", ex=30)
    assert client.get("aifam:test") == b"ok"
    assert 0 < client.ttl("aifam:test") <= 30


# —— TC-002-08：LiteLLM 网关 ——
def test_litellm_lists_three_backends():
    base = require("litellm")
    models = _get_json(base.rstrip("/") + "/v1/models")
    ids = {m.get("id", "") for m in models.get("data", [])}
    # 路由三后端（具体型号名以网关配置为准）
    assert ids, "LiteLLM /v1/models 为空"
    # TODO(req_impl): 断言含 DeepSeek/Kimi/Claude 三档 + per-user 预算计数 + 厂商 key 隔离（BUG-003）


# —— TC-002-09：Langfuse 可达 + trace 检索 ——
def test_langfuse_reachable():
    base = require("langfuse")
    # 健康检查；完整 trace 断言（token/cost/latency + trace_id 贯通）待 req_impl 接入 LiteLLM 出口
    with urllib.request.urlopen(base.rstrip("/") + "/api/public/health", timeout=10) as r:  # noqa: S310
        assert r.status == 200
    # TODO(req_impl): 发起一次经 LiteLLM 的调用 → 按 trace_id 检索 → 断言字段完整
