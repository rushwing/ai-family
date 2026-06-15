"""TC-002-11：基座 e2e 主链路（env-gated；req_impl + 起栈后启用）。

公网域名 → CF Access 登录 → IdP JWT → RLS 隔离读写 → Langfuse trace 贯通。
需 playwright + 完整栈，故默认 skip；设 AIFAMILY_BASE_URL 且装 playwright 后运行。
"""
import pytest

from conftest import require


def test_e2e_base_platform_happy_path():
    base = require("base_url")
    pytest.importorskip("playwright")
    pytest.skip(
        "e2e 主链路待 req_impl 起栈后实现："
        f"{base} → CF Access 登录 → OIDC JWT → 带 RLS 隔离的读写 → Langfuse 全链路 trace"
    )
    # TODO(req_impl): playwright 登录 + API 断言（跨成员 0 行 + trace_id 贯通）
