"""TC-002-04 / TC-002-05：PostgreSQL RLS 成员隔离 + 绕过封堵（BUG-002 核心）。

自包含：在测试库内建 demo 表 + RLS 策略 + 非超级 app 角色，验证 RLS *模式* 本身正确。
req_impl 把同一模式落进 data/migrations 的真实业务表（届时补针对真实表的断言）。

运行：设 AIFAMILY_PG_DSN（超级用户，用于建表/建角色）；CI 由 postgres service 提供。
"""
import os
import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("AIFAMILY_PG_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="设 AIFAMILY_PG_DSN 运行 RLS 集成用例")


@pytest.fixture()
def rls_table():
    with psycopg.connect(DSN, autocommit=True) as admin:
        admin.execute("DROP TABLE IF EXISTS rls_demo")
        admin.execute(
            "CREATE TABLE rls_demo (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), "
            "family_member_id text NOT NULL, body text)"
        )
        admin.execute("ALTER TABLE rls_demo ENABLE ROW LEVEL SECURITY")
        admin.execute("ALTER TABLE rls_demo FORCE ROW LEVEL SECURITY")
        admin.execute(
            "CREATE POLICY member_isolation ON rls_demo "
            "USING (family_member_id = current_setting('app.member_id', true)) "
            "WITH CHECK (family_member_id = current_setting('app.member_id', true))"
        )
        admin.execute(
            "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='aifam_app') "
            "THEN CREATE ROLE aifam_app NOLOGIN; END IF; END $$"
        )
        admin.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON rls_demo TO aifam_app")
        try:
            yield
        finally:
            admin.execute("DROP TABLE IF EXISTS rls_demo")


def _seed(member: str, body: str):
    with psycopg.connect(DSN) as conn, conn.transaction():
        conn.execute("SET LOCAL ROLE aifam_app")
        conn.execute("SELECT set_config('app.member_id', %s, true)", (member,))
        conn.execute("INSERT INTO rls_demo (family_member_id, body) VALUES (%s, %s)", (member, body))


def _select_as(member: str | None):
    with psycopg.connect(DSN) as conn, conn.transaction():
        conn.execute("SET LOCAL ROLE aifam_app")
        if member is not None:
            conn.execute("SELECT set_config('app.member_id', %s, true)", (member,))
        return conn.execute("SELECT family_member_id, body FROM rls_demo").fetchall()


# —— TC-002-04：正常路径，跨成员 0 行 ——
def test_cross_member_returns_zero(rls_table):
    _seed("A", "secret-A")
    _seed("B", "secret-B")
    assert _select_as("A") == [("A", "secret-A")]
    assert _select_as("B") == [("B", "secret-B")]  # B 看不到 A


def test_no_claim_returns_zero(rls_table):
    _seed("A", "secret-A")
    assert _select_as(None) == []  # 无 claim → 默认拒绝


# —— TC-002-05：绕过封堵（app 角色无 BYPASSRLS / FORCE RLS 生效 / WITH CHECK 防越权写）——
def test_app_role_has_no_bypass(rls_table):
    with psycopg.connect(DSN) as conn:
        row = conn.execute(
            "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname='aifam_app'"
        ).fetchone()
        assert row == (False, False)


def test_force_rls_enabled(rls_table):
    with psycopg.connect(DSN) as conn:
        row = conn.execute(
            "SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname='rls_demo'"
        ).fetchone()
        assert row == (True, True)


def test_with_check_blocks_cross_member_write(rls_table):
    # 以 A 身份尝试写入 B 的行 → WITH CHECK 拒绝
    with pytest.raises(psycopg.errors.Error):
        with psycopg.connect(DSN) as conn, conn.transaction():
            conn.execute("SET LOCAL ROLE aifam_app")
            conn.execute("SELECT set_config('app.member_id', 'A', true)")
            conn.execute("INSERT INTO rls_demo (family_member_id, body) VALUES ('B', 'spoof')")
