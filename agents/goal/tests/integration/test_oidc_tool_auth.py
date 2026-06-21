"""TC-003-02（A）：OIDC JWT 身份映射与 MCP 工具侧授权（agent 侧）。

需求 2 / 验收 #1。

env-gated：未设 AIFAMILY_OIDC_ISSUER 或工具侧 OIDC 鉴权模块（WP-2）尚未落地时 skip；
req_impl 接 Keycloak + 关闭 header 鉴权后转 passing。

登录链走共享 helper（真实 code+PKCE，tests/helpers/oidc）；被测对象 app.auth.oidc 只负责
验签 + 工具侧授权（避免依赖 SUT 自带登录助手）。
"""
import importlib.util
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


def test_member_scoped_tool_requires_member_fail_closed():
    """member-scoped 工具缺失 member 必须 fail-closed（防调用方遗漏 tenant scope 绕过）。"""
    token = login_role(ISSUER, "adult")
    with pytest.raises(oidc.AuthorizationError):
        oidc.authorize_tool(token, "list_targets")  # 缺 member → 拒
    me = oidc.verify_access_token(token)["family_member_id"]
    assert oidc.authorize_tool(token, "list_targets", member=me) is True  # 显式自有 → 允许
    # shared-scope 工具（目录）无需 member
    assert oidc.authorize_tool(token, "list_track_categories") is True


def _migrate_member(go_getter_id: int) -> str:
    """加载搬迁脚本的 _member（与迁移同源），确保 member-id 单一真值。"""
    path = Path(__file__).resolve().parents[2] / "scripts" / "migrate_mariadb_to_pg.py"
    spec = importlib.util.spec_from_file_location("_migrate_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod._member(go_getter_id)


def test_jwt_member_id_is_canonical_migration_rls_key():
    """端到端一致性：JWT 的 family_member_id == 迁移/RLS 使用的同一 member-id。

    否则网关把 JWT 身份写入 app.member_id 后，WP-1 迁移的数据将全部不可见。
    """
    mid = oidc.verify_access_token(login_role(ISSUER, "kid"))["family_member_id"]  # duoduo ↔ go_getter#1
    assert mid == _migrate_member(1), f"JWT member-id {mid!r} ≠ 迁移 RLS key {_migrate_member(1)!r}"

    pg_dsn = os.getenv("AIFAMILY_PG_DSN")
    if not pg_dsn:
        pytest.skip("设 AIFAMILY_PG_DSN 跑 JWT→RLS 端到端可见性断言")
    psycopg = pytest.importorskip("psycopg")
    mig = Path(__file__).resolve().parents[4] / "data" / "migrations" / "0002_goalagent_slice.sql"
    with psycopg.connect(pg_dsn, autocommit=True) as admin:
        admin.execute(mig.read_text(encoding="utf-8"))  # 幂等
        admin.execute(
            "INSERT INTO target (family_member_id, title) VALUES (%s, 'JWT-RLS probe')", (mid,)
        )

    def _count_as(member):
        c = psycopg.connect(pg_dsn)
        c.execute("BEGIN")
        c.execute("SET LOCAL ROLE aifam_app")
        c.execute("SELECT set_config('app.member_id', %s, true)", (member,))
        n = c.execute("SELECT count(*) FROM target WHERE title='JWT-RLS probe'").fetchone()[0]
        c.close()
        return n

    # 以 JWT 身份作为 app.member_id → 看得到同 id 落库的数据；换成员 → 看不到
    assert _count_as(mid) == 1, "JWT 身份作 app.member_id 时看不到同 id 数据（身份/RLS 不一致）"
    assert _count_as("member-other") == 0
