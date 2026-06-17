"""REQ-002 集成测试公共夹具（env-gated）。

服务连接信息从环境变量读取；未配置则相关用例 skip（tc_impl 阶段测试先行，
req_impl 起服务后转 passing）。CI 的 postgres service 提供 AIFAMILY_PG_DSN 跑 RLS 用例。
"""
import os
import pytest

ENV = {
    "pg": "AIFAMILY_PG_DSN",          # postgresql://user:pwd@host:5432/db
    "oidc": "AIFAMILY_OIDC_ISSUER",   # https://idp/realms/family
    "redis": "AIFAMILY_REDIS_URL",    # redis://host:6379/0
    "litellm": "AIFAMILY_LITELLM_URL",
    "langfuse": "AIFAMILY_LANGFUSE_URL",
    "base_url": "AIFAMILY_BASE_URL",  # 公网域名（e2e）
}


def require(service: str) -> str:
    val = os.getenv(ENV[service])
    if not val:
        pytest.skip(f"未设 {ENV[service]}，跳过 {service} 集成用例（req_impl 起服务后启用）")
    return val
