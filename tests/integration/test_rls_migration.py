"""TC-002-04/05 真表版：应用 data/migrations/0001_rls_foundation.sql 后断言真实表隔离。

把 RLS *模式*（test_rls.py）落到真实业务表 member_note + 平台审计表 audit_log：
- member_note：跨成员 0 行 / 无 claim 0 行 / FORCE RLS / WITH CHECK 拒越权写（BUG-002）
- audit_log：app 角色可 INSERT、不可 UPDATE/DELETE（append-only，BUG-011/015）、跨成员读 0 行

运行：设 AIFAMILY_PG_DSN（超级用户）；CI 由 postgres service 提供。
"""
import os
from pathlib import Path

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("AIFAMILY_PG_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="设 AIFAMILY_PG_DSN 运行迁移 RLS 用例")

MIGRATION = Path(__file__).resolve().parents[2] / "data" / "migrations" / "0001_rls_foundation.sql"


@pytest.fixture(scope="module", autouse=True)
def apply_migration():
    with psycopg.connect(DSN, autocommit=True) as admin:
        # 干净起点 + 应用迁移（幂等）
        admin.execute("DROP TABLE IF EXISTS member_note, audit_log")
        admin.execute(MIGRATION.read_text(encoding="utf-8"))
        yield
        admin.execute("DROP TABLE IF EXISTS member_note, audit_log")


def _txn(member=None):
    conn = psycopg.connect(DSN)
    conn.execute("BEGIN")
    conn.execute("SET LOCAL ROLE aifam_app")
    if member is not None:
        conn.execute("SELECT set_config('app.member_id', %s, true)", (member,))
    return conn


def test_member_note_cross_member_zero():
    c = _txn("A"); c.execute("INSERT INTO member_note(family_member_id, body) VALUES ('A','a')"); c.commit(); c.close()
    c = _txn("B"); rows = c.execute("SELECT body FROM member_note").fetchall(); c.close()
    assert rows == []


def test_member_note_no_claim_zero():
    c = _txn("A"); c.execute("INSERT INTO member_note(family_member_id, body) VALUES ('A','a')"); c.commit(); c.close()
    c = _txn(None); rows = c.execute("SELECT * FROM member_note").fetchall(); c.close()
    assert rows == []


def test_member_note_with_check_blocks_spoof():
    with pytest.raises(psycopg.errors.Error):
        c = _txn("A")
        c.execute("INSERT INTO member_note(family_member_id, body) VALUES ('B','spoof')")
        c.commit()


def test_audit_append_only_no_update_delete():
    # app 角色可 INSERT
    c = _txn("A"); c.execute("INSERT INTO audit_log(family_member_id, actor, action) VALUES ('A','A','login')"); c.commit(); c.close()
    # 不可 UPDATE / DELETE（仅授 SELECT,INSERT → 权限拒绝）
    for sql in ("UPDATE audit_log SET action='x'", "DELETE FROM audit_log"):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            c = _txn("A"); c.execute(sql); c.commit()


def test_audit_cross_member_read_zero():
    c = _txn("A"); c.execute("INSERT INTO audit_log(family_member_id, actor, action) VALUES ('A','A','login')"); c.commit(); c.close()
    c = _txn("B"); rows = c.execute("SELECT * FROM audit_log").fetchall(); c.close()
    assert rows == []


def test_audit_cross_member_write_blocked():
    # claim=A 不能伪造 family_member_id='B' 的审计行（evaluator-001 round-1 缺口回归）
    with pytest.raises(psycopg.errors.Error):
        c = _txn("A")
        c.execute("INSERT INTO audit_log(family_member_id, actor, action) VALUES ('B','A','spoof')")
        c.commit()
