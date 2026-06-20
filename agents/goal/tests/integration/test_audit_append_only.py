"""TC-003-06：审计独立 schema 的 append-only 与 kid 不可删除。

需求 6 / 验收 #6；回归 BUG-011 / BUG-015。

env-gated：未设 AIFAMILY_PG_DSN 或独立 audit schema（WP-6）尚未落地时 skip；
req_impl 起 PG + audit schema 后转 passing。
"""
import os

import pytest

psycopg = pytest.importorskip("psycopg")

DSN = os.getenv("AIFAMILY_PG_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="设 AIFAMILY_PG_DSN 运行审计 append-only 用例")

AUDIT_TABLE = "audit.event"  # 独立 schema，与可删会话历史物理分离
SESSION_TABLE = "chat.session_message"


@pytest.fixture(scope="module", autouse=True)
def require_audit_schema():
    with psycopg.connect(DSN, autocommit=True) as admin:
        exists = admin.execute(
            "SELECT 1 FROM information_schema.schemata WHERE schema_name = 'audit'"
        ).fetchone()
    if not exists:
        pytest.skip("独立 audit schema 尚未落地（WP-6，req_impl 起）")


def _txn(member=None, role="aifam_app"):
    conn = psycopg.connect(DSN)
    conn.execute("BEGIN")
    conn.execute(f"SET LOCAL ROLE {role}")
    if member is not None:
        conn.execute("SELECT set_config('app.member_id', %s, true)", (member,))
    return conn


def _seed_audit(member, actor, action):
    c = _txn(member)
    c.execute(
        f"INSERT INTO {AUDIT_TABLE} (family_member_id, actor, action) VALUES (%s,%s,%s)",
        (member, actor, action),
    )
    c.commit()
    c.close()


def test_audit_and_session_history_physically_separated():
    with psycopg.connect(DSN, autocommit=True) as admin:
        audit_schema = admin.execute(
            "SELECT table_schema FROM information_schema.tables WHERE table_name='event' "
            "AND table_schema='audit'"
        ).fetchone()
        session_schema = admin.execute(
            "SELECT table_schema FROM information_schema.tables "
            "WHERE table_name='session_message'"
        ).fetchone()
    assert audit_schema and audit_schema[0] == "audit"
    assert session_schema and session_schema[0] != "audit", "审计与会话历史须不同 schema"


@pytest.mark.parametrize("role", ["aifam_app", "aifam_kid"])
def test_no_update_delete_truncate_on_audit(role):
    _seed_audit("A", "A", "login")
    for sql in (
        f"UPDATE {AUDIT_TABLE} SET action='x'",
        f"DELETE FROM {AUDIT_TABLE}",
        f"TRUNCATE {AUDIT_TABLE}",
    ):
        with pytest.raises(psycopg.errors.Error):
            c = _txn("A", role=role)
            c.execute(sql)
            c.commit()


def test_audit_survives_session_soft_delete():
    _seed_audit("kid", "kid", "checkin")
    c = _txn("kid")
    # kid 软删自己的会话记录
    c.execute(f"UPDATE {SESSION_TABLE} SET deleted_at = now() WHERE family_member_id='kid'")
    c.commit()
    c.close()
    # 家长审计读侧仍能查到 kid 的操作记录
    c = _txn(role="aifam_audit_reader")
    rows = c.execute(
        f"SELECT action FROM {AUDIT_TABLE} WHERE family_member_id='kid' AND actor='kid'"
    ).fetchall()
    c.close()
    assert ("checkin",) in rows, "kid 删会话不得使审计行消失（BUG-011）"


def test_app_role_lacks_update_delete_grant():
    with psycopg.connect(DSN, autocommit=True) as admin:
        privs = admin.execute(
            "SELECT privilege_type FROM information_schema.role_table_grants "
            "WHERE table_schema='audit' AND table_name='event' AND grantee='aifam_app'"
        ).fetchall()
    granted = {p[0] for p in privs}
    assert "UPDATE" not in granted and "DELETE" not in granted
    assert "INSERT" in granted, "应用 role 只授追加所需权限"


def test_other_member_still_read_isolated():
    _seed_audit("A", "A", "login")
    c = _txn("B")
    rows = c.execute(f"SELECT * FROM {AUDIT_TABLE} WHERE family_member_id='A'").fetchall()
    c.close()
    assert rows == [], "非家长其他成员仍受读侧 RLS 隔离"
