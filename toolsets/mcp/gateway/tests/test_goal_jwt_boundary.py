"""TC-003-02（B）：MCP 网关对 GoalAgent 工具的工具侧 JWT 边界。

需求 2 / 验收 #1。

env-gated：未设 AIFAMILY_GATEWAY_URL（运行中的 MCP 网关）时 skip；
req_impl 起网关 + OIDC 后转 passing。该目录的用例随 REQ-005 workspace 接 CI。

BUG-031 修复：登录 helper 统一为 tests/helpers/oidc.login_role；OIDC 环境齐备时
若 helper 缺失/导入失败应使用例失败（ImportError），不再静默 skip。
"""
import os
import sys
from pathlib import Path

import pytest

httpx = pytest.importorskip("httpx")

GATEWAY = os.getenv("AIFAMILY_GATEWAY_URL")
pytestmark = pytest.mark.skipif(not GATEWAY, reason="设 AIFAMILY_GATEWAY_URL 运行网关 JWT 边界用例")

# 让 tests/helpers 可被本模块（不同 module 树）导入；REQ-005 workspace 接 CI 后由 pythonpath 统一。
_TESTS_DIR = Path(__file__).resolve().parents[4] / "tests"
if _TESTS_DIR.is_dir() and str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))


def _token(role: str) -> str:
    issuer = os.getenv("AIFAMILY_OIDC_ISSUER")
    if not issuer:
        pytest.skip("设 AIFAMILY_OIDC_ISSUER 取真实 token")
    # 环境齐备但 helper 缺失 → 让 ImportError 冒泡为用例失败（不静默 skip）
    from helpers.oidc import login_role

    return login_role(issuer, role)


def _call(tool: str, token: str | None = None, *, headers=None):
    h = dict(headers or {})
    if token is not None:
        h["Authorization"] = f"Bearer {token}"
    return httpx.post(f"{GATEWAY}/tools/{tool}", json={}, headers=h, timeout=10)


def test_missing_token_rejected():
    assert _call("list_targets").status_code == 401


def test_legacy_telegram_header_rejected():
    r = _call("list_targets", headers={"X-Telegram-Chat-Id": "123"})
    assert r.status_code == 401, "旧 header 鉴权必须在网关被拒"


def test_tampered_token_rejected():
    assert _call("list_targets", token="not.a.valid.jwt").status_code == 401


def test_kid_blocked_from_adult_write():
    assert _call("create_target", token=_token("kid")).status_code == 403


def test_cross_member_param_rejected():
    # 成员 A（adult）的 token 操作成员 B 的资源 → 拒
    r = httpx.post(
        f"{GATEWAY}/tools/list_targets",
        json={"family_member_id": "B"},
        headers={"Authorization": f"Bearer {_token('adult')}"},
        timeout=10,
    )
    assert r.status_code == 403
