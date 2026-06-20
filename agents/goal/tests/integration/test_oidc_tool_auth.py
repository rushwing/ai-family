"""TC-003-02（A）：OIDC JWT 身份映射与 MCP 工具侧授权（agent 侧）。

需求 2 / 验收 #1。

env-gated：未设 AIFAMILY_OIDC_ISSUER 或工具侧 OIDC 鉴权模块（WP-2）尚未落地时 skip；
req_impl 接 Keycloak + 关闭 header 鉴权后转 passing。

登录链走共享 helper（真实 code+PKCE，tests/helpers/oidc）；被测对象 app.auth.oidc 只负责
验签 + 工具侧授权（避免依赖 SUT 自带登录助手）。
"""
import os
import sys
from pathlib import Path

import pytest

ISSUER = os.getenv("AIFAMILY_OIDC_ISSUER")
pytestmark = pytest.mark.skipif(not ISSUER, reason="设 AIFAMILY_OIDC_ISSUER 运行 OIDC 工具鉴权用例")

# WP-2 落地的工具侧鉴权（替换 X-Telegram-Chat-Id header）—— 被测对象
oidc = pytest.importorskip("app.auth.oidc", reason="工具侧 OIDC 鉴权未落地（WP-2）")

# 共享登录 helper（环境齐备时缺失 → ImportError 冒泡为失败，不静默 skip）
_TESTS_DIR = Path(__file__).resolve().parents[4] / "tests"
if _TESTS_DIR.is_dir() and str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))
from helpers.oidc import login_role  # noqa: E402


# best_pal→admin / go_getter→adult·kid 映射 + 成员身份取自验证后的 JWT
@pytest.mark.parametrize("role", ["admin", "adult", "kid"])
def test_role_mapping_from_verified_jwt(role):
    claims = oidc.verify_access_token(login_role(ISSUER, role))
    assert claims["role"] == role
    assert claims.get("sub") and claims.get("family_member_id")


def test_kid_can_only_run_own_checkin():
    token = login_role(ISSUER, "kid")
    member = oidc.verify_access_token(token)["family_member_id"]
    # kid 自有 Draft-First 打卡 → 允许
    assert oidc.authorize_tool(token, "checkin_task", member=member) is True
    # 成人/管理写、跨成员 → 拒
    for tool, m in [("create_target", member), ("confirm_goal_group", member), ("list_targets", "OTHER")]:
        with pytest.raises(oidc.AuthorizationError):
            oidc.authorize_tool(token, tool, member=m)


@pytest.mark.parametrize("bad", ["missing", "expired", "tampered", "legacy_header"])
def test_invalid_credentials_rejected(bad):
    with pytest.raises(oidc.AuthenticationError):
        oidc.authorize_tool(oidc.sample_bad_token(bad), "list_targets", member="A")


def test_cross_member_request_rejected():
    token = login_role(ISSUER, "adult")  # 成员 A
    with pytest.raises(oidc.AuthorizationError):
        oidc.authorize_tool(token, "list_targets", member="OTHER")
