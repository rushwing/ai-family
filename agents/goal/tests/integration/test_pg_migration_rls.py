"""TC-003-01：GoalAgent MariaDB→PG16 迁移与业务/平台表 RLS 内建。

需求 1 / 验收 #1·#7；回归 BUG-002 / BUG-014。

env-gated（REQ-002 范式）：未设 AIFAMILY_PG_DSN（超级用户）或 GoalAgent PG 迁移
尚未落地（WP-1）时整模块 skip；req_impl 起 PG + 迁移后转 passing。

BUG-031 round-3 修复：
- fixture 补齐必填 `vacation_type` 等，并加 fixture 自加载 smoke test（证明能在真实 MariaDB
  schema 上加载）。
- RLS 逐表 seed 改为**依赖顺序的 FK 感知 factory**：递归解析 PG 外键、按拓扑序先建父行（同成员）、
  enum 取合法 label、family_member_id 一致传播——不再把 FK 一律写 0（那会先触发 FK 错误，
  证明不了隔离）。随后以应用角色验跨成员 SELECT=0 + 伪造 family_member_id 写被 WITH CHECK 拒。
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

psycopg = pytest.importorskip("psycopg")

DSN = os.getenv("AIFAMILY_PG_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="设 AIFAMILY_PG_DSN 运行 GoalAgent 迁移 RLS 用例")

REPO = Path(__file__).resolve().parents[4]
MIGRATIONS_DIR = REPO / "data" / "migrations"
CHECK_RLS = REPO / "tools" / "check_rls.py"
MARIADB_FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "mariadb_seed.sql"
MIGRATE_SCRIPT = REPO / "agents" / "goal" / "scripts" / "migrate_mariadb_to_pg.py"

BUSINESS_TABLES = ["go_getter", "target", "plan", "weekly_milestone", "task", "check_in", "report"]
PLATFORM_TABLES = ["lg_checkpoint", "outbox", "audit.event", "confirm_token", "tool_call_log"]
TENANT_TABLES = BUSINESS_TABLES + PLATFORM_TABLES

SRC_TO_PG = {
    "go_getters": "go_getter",
    "targets": "target",
    "plans": "plan",
    "weekly_milestones": "weekly_milestone",
    "tasks": "task",
    "check_ins": "check_in",
    "reports": "report",
}


def _split(table: str) -> tuple[str, str]:
    schema, _, name = table.rpartition(".")
    return (schema or "public", name)


def _goalagent_migrations() -> list[Path]:
    if not MIGRATIONS_DIR.exists():
        return []
    return sorted(p for p in MIGRATIONS_DIR.glob("*.sql") if p.name > "0001")


@pytest.fixture(scope="module", autouse=True)
def apply_migration():
    migs = _goalagent_migrations()
    if not migs:
        pytest.skip("GoalAgent PG 迁移尚未落地（WP-1，req_impl 起）")
    with psycopg.connect(DSN, autocommit=True) as admin:
        for m in migs:
            admin.execute(m.read_text(encoding="utf-8"))
        yield


def _txn(member=None, role="aifam_app"):
    conn = psycopg.connect(DSN)
    conn.execute("BEGIN")
    conn.execute(f"SET LOCAL ROLE {role}")
    if member is not None:
        conn.execute("SELECT set_config('app.member_id', %s, true)", (member,))
    return conn


# ───────────────────── FK 感知依赖顺序 seeder（PG 目标 schema） ─────────────────────


# 注：introspection 用独立 `admin`（超级用户）连接——`information_schema` 的
# key_column_usage/constraint_column_usage 按当前角色权限过滤，在 aifam_app 角色下查不到
# 外键，会导致 FK 列被当普通整数填 0。写入仍走 `conn`（aifam_app + claim）。


def _pk_col(admin, schema, name):
    r = admin.execute(
        "SELECT a.attname FROM pg_index i "
        "JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum = ANY(i.indkey) "
        "JOIN pg_class c ON c.oid=i.indrelid JOIN pg_namespace n ON n.oid=c.relnamespace "
        "WHERE i.indisprimary AND c.relname=%s AND n.nspname=%s LIMIT 1",
        (name, schema),
    ).fetchone()
    return r[0] if r else "id"


def _fk_map(admin, schema, name):
    # pg_catalog 按 ordinality 正确配对本地↔引用列，支持复合外键；
    # （information_schema 对复合 FK 会因 constraint_name 交叉连接而错配。）
    rows = admin.execute(
        "SELECT att.attname, rns.nspname, rel.relname, fatt.attname "
        "FROM pg_constraint con "
        "JOIN pg_class c ON c.oid=con.conrelid "
        "JOIN pg_namespace cns ON cns.oid=c.relnamespace "
        "JOIN pg_class rel ON rel.oid=con.confrelid "
        "JOIN pg_namespace rns ON rns.oid=rel.relnamespace "
        "JOIN LATERAL unnest(con.conkey) WITH ORDINALITY AS lk(attnum, ord) ON true "
        "JOIN LATERAL unnest(con.confkey) WITH ORDINALITY AS fk(attnum, ord) ON fk.ord=lk.ord "
        "JOIN pg_attribute att ON att.attrelid=con.conrelid AND att.attnum=lk.attnum "
        "JOIN pg_attribute fatt ON fatt.attrelid=con.confrelid AND fatt.attnum=fk.attnum "
        "WHERE con.contype='f' AND c.relname=%s AND cns.nspname=%s",
        (name, schema),
    ).fetchall()
    return {r[0]: (r[1], r[2], r[3]) for r in rows}


def _enum_label(admin, udt_name):
    r = admin.execute(
        "SELECT e.enumlabel FROM pg_enum e JOIN pg_type t ON t.oid=e.enumtypid "
        "WHERE t.typname=%s ORDER BY e.enumsortorder LIMIT 1",
        (udt_name,),
    ).fetchone()
    return r[0] if r else "x"


def _fields_values(conn, admin, table, member, cache):
    """构造 `table` 在 `member` 下的一行（fields, values），按需递归先建父行（同成员）。"""
    schema, name = _split(table)
    cols = admin.execute(
        "SELECT column_name, data_type, udt_name, is_nullable, column_default "
        "FROM information_schema.columns WHERE table_schema=%s AND table_name=%s",
        (schema, name),
    ).fetchall()
    fks = _fk_map(admin, schema, name)
    fields, values = [], []
    for col, dtype, udt, is_nullable, default in cols:
        if not (is_nullable == "NO" and default is None):
            continue  # 可空或有默认（含 serial PK）→ 交给 DB
        if col == "family_member_id":
            fields.append(col); values.append(member)
        elif col in fks:
            rs, rt, _rc = fks[col]
            fields.append(col); values.append(_seed(conn, admin, f"{rs}.{rt}", member, cache))
        elif dtype == "USER-DEFINED":
            fields.append(col); values.append(_enum_label(admin, udt))
        elif dtype in ("integer", "bigint", "numeric", "smallint", "real", "double precision"):
            fields.append(col); values.append(0)
        elif dtype == "boolean":
            fields.append(col); values.append(False)
        elif "timestamp" in dtype or dtype == "date":
            fields.append(col); values.append("2026-01-01")
        elif dtype in ("json", "jsonb"):
            fields.append(col); values.append("{}")
        else:
            fields.append(col); values.append("x")
    return fields, values


def _seed(conn, admin, table, member, cache):
    """插入一行（及其必填父行），返回该行 PK 值；按 (table, member) 缓存避免重复。"""
    key = (table, member)
    if key in cache:
        return cache[key]
    schema, name = _split(table)
    fields, values = _fields_values(conn, admin, table, member, cache)
    pk = _pk_col(admin, schema, name)
    placeholders = ", ".join(["%s"] * len(fields))
    row = conn.execute(
        f'INSERT INTO {table} ({", ".join(fields)}) VALUES ({placeholders}) RETURNING {pk}',
        values,
    ).fetchone()
    cache[key] = row[0]
    return row[0]


# ───────────────────────── (A) MariaDB→PG 真实搬迁校验 ─────────────────────────


def _mysql_conn(mysql_dsn: str):
    pymysql = pytest.importorskip("pymysql")
    import urllib.parse as up

    u = up.urlparse(mysql_dsn)
    return pymysql.connect(
        host=u.hostname, port=u.port or 3306, user=u.username,
        password=u.password or "", database=u.path.lstrip("/"), autocommit=True,
    )


def _load_mariadb_fixture(conn):
    if not MARIADB_FIXTURE.exists():
        pytest.skip("MariaDB fixture 缺失")
    with conn.cursor() as cur:
        for stmt in MARIADB_FIXTURE.read_text(encoding="utf-8").split(";\n"):
            if stmt.strip():
                cur.execute(stmt)


def test_mariadb_fixture_loads_on_real_schema():
    """fixture 自加载 smoke test：证明能在真实 goal-agent MariaDB schema 上加载（含全部必填字段）。"""
    mysql_dsn = os.getenv("AIFAMILY_MARIADB_DSN")
    if not mysql_dsn:
        pytest.skip("设 AIFAMILY_MARIADB_DSN（含 goal-agent schema 的源库）运行 fixture smoke test")
    conn = _mysql_conn(mysql_dsn)
    try:
        _load_mariadb_fixture(conn)
        with conn.cursor() as cur:
            for t in ("best_pals", "go_getters", "targets", "plans", "tasks", "check_ins", "reports"):
                cur.execute(f"SELECT count(*) FROM {t}")
                assert cur.fetchone()[0] >= 2, f"fixture 未在 {t} 写入预期行"
    finally:
        conn.close()


def _run_migrate(mysql_dsn: str):
    """执行一次 MariaDB→PG 数据搬迁脚本（WP-1）。"""
    res = subprocess.run(
        [sys.executable, str(MIGRATE_SCRIPT)],
        capture_output=True, text=True,
        env={**os.environ, "AIFAMILY_MARIADB_DSN": mysql_dsn, "AIFAMILY_PG_DSN": DSN},
    )
    assert res.returncode == 0, f"搬迁脚本失败：{res.stderr}"


def _migration_snapshot():
    """搬迁结果快照：各 SRC_TO_PG 目标表计数 + target/plan 业务键集合 + target↔plan 关联。"""
    with psycopg.connect(DSN, autocommit=True) as admin:
        counts = {
            pg: admin.execute(f"SELECT count(*) FROM {pg}").fetchone()[0]
            for pg in SRC_TO_PG.values()
        }
        target_titles = {r[0] for r in admin.execute("SELECT title FROM target").fetchall()}
        plan_titles = {r[0] for r in admin.execute("SELECT title FROM plan").fetchall()}
        relation = {
            (r[0], r[1])
            for r in admin.execute(
                "SELECT p.title, t.title FROM plan p JOIN target t ON t.id = p.target_id"
            ).fetchall()
        }
    return counts, target_titles, plan_titles, relation


@pytest.fixture
def migrated():
    mysql_dsn = os.getenv("AIFAMILY_MARIADB_DSN")
    if not mysql_dsn:
        pytest.skip("设 AIFAMILY_MARIADB_DSN 运行搬迁校验")
    if not MIGRATE_SCRIPT.exists():
        pytest.skip("搬迁脚本尚未落地（WP-1）")
    src = _mysql_conn(mysql_dsn)
    _load_mariadb_fixture(src)
    _run_migrate(mysql_dsn)
    yield src, mysql_dsn
    src.close()


def test_migration_preserves_counts(migrated):
    src, _ = migrated
    with src.cursor() as cur:
        for src_table, pg_table in SRC_TO_PG.items():
            cur.execute(f"SELECT count(*) FROM {src_table}")
            src_n = cur.fetchone()[0]
            with psycopg.connect(DSN, autocommit=True) as admin:
                pg_n = admin.execute(f"SELECT count(*) FROM {pg_table}").fetchone()[0]
            assert pg_n == src_n, f"{src_table}->{pg_table} 计数不符：源 {src_n} 目标 {pg_n}"


def test_data_migration_is_idempotent(migrated):
    """连续执行**数据搬迁脚本**两次：计数 / 业务键集合 / target↔plan 关联三者不变（TC-003-01 步骤1）。

    与 schema 迁移幂等（test_schema_migration_idempotent）区分——后者只证建表 SQL 可重放，
    不能证明重复搬迁不产生重复业务记录。
    """
    _src, mysql_dsn = migrated
    snap1 = _migration_snapshot()       # 第一次搬迁后（fixture 已跑一次）
    _run_migrate(mysql_dsn)             # 第二次搬迁
    snap2 = _migration_snapshot()
    counts1, t1, p1, rel1 = snap1
    counts2, t2, p2, rel2 = snap2
    assert counts2 == counts1, f"二次搬迁产生重复业务记录：{counts1} → {counts2}"
    assert t2 == t1, "二次搬迁改变了 target 业务键集合"
    assert p2 == p1, "二次搬迁改变了 plan 业务键集合"
    assert rel2 == rel1, "二次搬迁改变了 target↔plan 关联"


def test_migration_preserves_fields_and_relations(migrated):
    with psycopg.connect(DSN, autocommit=True) as admin:
        titles = {r[0] for r in admin.execute("SELECT title FROM target").fetchall()}
        assert {"Math Mastery A", "Reading Habit B"} <= titles
        row = admin.execute(
            "SELECT t.title FROM plan p JOIN target t ON t.id = p.target_id WHERE p.title='Plan A'"
        ).fetchone()
        assert row and row[0] == "Math Mastery A", "搬迁未保留 target↔plan 关联"


def test_migration_is_lossless(migrated):
    """搬迁不丢字段：逐表与源按列顺序比对（描述/日期/优先级/vacation/XP·streak/打卡详情/报告周期）。"""
    src, _ = migrated

    def _both(cur, mysql_sql, pg_sql, admin):
        cur.execute(mysql_sql)
        s = tuple(cur.fetchone())
        return tuple(admin.execute(pg_sql).fetchone()), s

    with src.cursor() as cur, psycopg.connect(DSN, autocommit=True) as admin:
        p, s = _both(cur,
            "SELECT description, vacation_type, vacation_year, priority FROM targets WHERE id=1",
            "SELECT description, vacation_type, vacation_year, priority FROM target WHERE id=1", admin)
        assert p == s, f"target 描述/vacation/优先级丢失：源 {s} 目标 {p}"

        p, s = _both(cur,
            "SELECT xp_total, streak_current, streak_longest FROM go_getters WHERE id=1",
            "SELECT xp_total, streak_current, streak_longest FROM go_getter "
            "WHERE family_member_id='member-go-1'", admin)
        assert p == s, f"go_getter XP/streak 丢失：源 {s} 目标 {p}"

        p, s = _both(cur,
            "SELECT status, xp_earned, streak_at_checkin, duration_minutes, notes "
            "FROM check_ins WHERE id=1",
            "SELECT status, xp_earned, streak_at_checkin, duration_minutes, notes "
            "FROM check_in WHERE id=1", admin)
        assert p == s, f"打卡详情丢失：源 {s} 目标 {p}"

        p, s = _both(cur,
            "SELECT period_start, period_end FROM reports WHERE id=1",
            "SELECT period_start, period_end FROM report WHERE id=1", admin)
        assert p == s, f"报告周期丢失：源 {s} 目标 {p}"


def test_migration_partitions_members(migrated):
    with psycopg.connect(DSN, autocommit=True) as admin:
        a = admin.execute("SELECT family_member_id FROM target WHERE title='Math Mastery A'").fetchone()[0]
        b = admin.execute("SELECT family_member_id FROM target WHERE title='Reading Habit B'").fetchone()[0]
    assert a and b and a != b, "两个 go_getter 的数据须映射到不同 family_member_id"


# ───────────────────── (B) 逐表 RLS 行为 + 结构 + 扫描门 ─────────────────────


def test_schema_migration_idempotent():
    """**仅** schema 迁移（建表 SQL）可重放幂等——不作为数据搬迁幂等证据（见 test_data_migration_is_idempotent）。"""
    migs = _goalagent_migrations()
    with psycopg.connect(DSN, autocommit=True) as admin:
        before = admin.execute("SELECT count(*) FROM target").fetchone()[0]
        for m in migs:
            admin.execute(m.read_text(encoding="utf-8"))
        after = admin.execute("SELECT count(*) FROM target").fetchone()[0]
    assert before == after, "重放 schema 迁移 SQL 不应改变业务计数"


@pytest.mark.parametrize("table", TENANT_TABLES)
def test_tenant_table_has_member_scope_and_force_rls(table):
    schema, name = _split(table)
    with psycopg.connect(DSN, autocommit=True) as admin:
        colnames = {
            c[0] for c in admin.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema=%s AND table_name=%s", (schema, name),
            ).fetchall()
        }
        rls = admin.execute(
            "SELECT c.relrowsecurity, c.relforcerowsecurity FROM pg_class c "
            "JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relname=%s AND n.nspname=%s",
            (name, schema),
        ).fetchone()
    assert "family_member_id" in colnames, f"{table} 缺 family_member_id（或须显式 shared scope）"
    assert rls == (True, True), f"{table} 须 ENABLE + FORCE RLS（BUG-002/014），实际 {rls}"


@pytest.mark.parametrize("table", TENANT_TABLES)
def test_tenant_table_rls_behavior_blocks_cross_member(table):
    """依赖顺序 factory 建 M1 真实子树 → 跨成员 SELECT=0 + WITH CHECK 拒（捕获 USING(true) 泄漏）。"""
    cache: dict = {}
    admin = psycopg.connect(DSN, autocommit=True)  # introspection 走超级用户（避开 info_schema 角色过滤）
    try:
        # 1) M1 真实子树（FK 解析到 M1 父行），提交
        c = _txn("M1")
        _seed(c, admin, table, "M1", cache)
        c.commit()
        c.close()
        # 2) M2 看不到 M1 的行（USING(true) 会在此泄漏 → 断言失败）
        c = _txn("M2")
        leaked = c.execute(f"SELECT count(*) FROM {table} WHERE family_member_id='M1'").fetchone()[0]
        c.close()
        assert leaked == 0, f"{table}：跨成员读到 M1 数据（疑似 USING(true) 泄漏）"
        # 3) M1 claim 伪造 family_member_id=M2（复用已提交 M1 父行，FK 合法）→ WITH CHECK 拒
        c = _txn("M1")
        fields, values = _fields_values(c, admin, table, "M1", cache)  # cache 命中已提交父行，不重插
        values = ["M2" if f == "family_member_id" else v for f, v in zip(fields, values)]
        placeholders = ", ".join(["%s"] * len(fields))
        with pytest.raises(psycopg.errors.Error):
            c.execute(f'INSERT INTO {table} ({", ".join(fields)}) VALUES ({placeholders})', values)
            c.commit()
        c.close()
    finally:
        admin.close()


@pytest.mark.parametrize(
    "child,parent_col,parent",
    [
        ("plan", "target_id", "target"),
        ("weekly_milestone", "plan_id", "plan"),
        ("task", "milestone_id", "weekly_milestone"),
        ("check_in", "task_id", "task"),
    ],
)
def test_cross_member_fk_rejected(child, parent_col, parent):
    """成员 A 不得用成员 B 的 parent_id 建立子行（复合 FK 强制父子同租户，堵 BUG-002 侧信道）。"""
    admin = psycopg.connect(DSN, autocommit=True)
    try:
        # B 建一个父行，拿到其 id
        cb = _txn("B")
        b_parent_id = _seed(cb, admin, f"public.{parent}", "B", {})
        cb.commit()
        cb.close()
        # 为 A 构造一个合法子行（含 A 自己的父链），再把父列改成 B 的 id
        ca = _txn("A")
        fields, values = _fields_values(ca, admin, f"public.{child}", "A", {})
        values = [b_parent_id if f == parent_col else v for f, v in zip(fields, values)]
        placeholders = ", ".join(["%s"] * len(fields))
        # 复合 FK 找不到 (A, b_parent_id) → 拒（堵跨成员关系 / 存在性侧信道）
        with pytest.raises(psycopg.errors.Error):
            ca.execute(f'INSERT INTO {child} ({", ".join(fields)}) VALUES ({placeholders})', values)
            ca.commit()
        ca.close()
    finally:
        admin.close()


def test_app_role_has_no_bypassrls():
    with psycopg.connect(DSN, autocommit=True) as admin:
        bypass = admin.execute(
            "SELECT rolbypassrls FROM pg_roles WHERE rolname = 'aifam_app'"
        ).fetchone()[0]
    assert bypass is False, "应用 role 不得具 BYPASSRLS"


def _run_check_rls(mig_dir=None):
    if not CHECK_RLS.exists():
        pytest.skip("tools/check_rls.py 尚未就位")
    argv = [sys.executable, str(CHECK_RLS)] + ([str(mig_dir)] if mig_dir else [])
    return subprocess.run(argv, capture_output=True, text=True)


def test_check_rls_passes_on_managed_migrations():
    assert _run_check_rls().returncode == 0, "仓库迁移的 RLS 扫描应通过"


def test_check_rls_fails_on_migration_without_rls(tmp_path):
    (tmp_path / "9001_no_rls.sql").write_text(
        "CREATE TABLE bad_no_rls (family_member_id text);", encoding="utf-8"
    )
    assert _run_check_rls(tmp_path).returncode != 0, "无 RLS 新表的迁移应令扫描失败（BUG-002）"


def test_check_rls_fails_on_bare_security_definer(tmp_path):
    (tmp_path / "9002_sd.sql").write_text(
        "CREATE FUNCTION bad_sd() RETURNS int LANGUAGE sql SECURITY DEFINER AS $$ SELECT 1 $$;",
        encoding="utf-8",
    )
    assert _run_check_rls(tmp_path).returncode != 0, "裸 SECURITY DEFINER 的迁移应令扫描失败"
