#!/usr/bin/env python3
"""MariaDB(goal-agent) → PostgreSQL 16 数据搬迁（REQ-003 WP-1 / TC-003-01）。

设计要点：
  * **幂等**：每次全量重载（TRUNCATE … RESTART IDENTITY CASCADE → 按 FK 顺序重插 → setval）；
    二次执行结果一致（计数 / 业务键 / 关联不变），不产生重复业务记录。
  * **保留源主键**：以源 id 显式插入，维持 target↔plan↔milestone↔task↔check_in 关系。
  * **成员归属**：go_getter → family_member_id 映射（按成员落 PG，启用 RLS）。
  * 目标库以**超级用户**连接（AIFAMILY_PG_DSN，搬迁期绕 RLS 直写）。

env：AIFAMILY_MARIADB_DSN（源）、AIFAMILY_PG_DSN（目标，超级用户）。

注：data/migrations/0002 的 schema 须先应用（业务/平台表已建）。本脚本只搬数据。
"""
from __future__ import annotations

import os
import sys
import urllib.parse as up


def _member(go_getter_id: int) -> str:
    """go_getter → family_member_id（每个 go_getter 一个稳定且互异的成员 id）。"""
    return f"member-go-{go_getter_id}"


def _mysql(dsn: str):
    import pymysql

    u = up.urlparse(dsn)
    return pymysql.connect(
        host=u.hostname, port=u.port or 3306, user=u.username,
        password=u.password or "", database=u.path.lstrip("/"),
        cursorclass=pymysql.cursors.DictCursor,
    )


def main() -> int:
    mysql_dsn = os.environ["AIFAMILY_MARIADB_DSN"]
    pg_dsn = os.environ["AIFAMILY_PG_DSN"]
    import psycopg

    my = _mysql(mysql_dsn)

    def fetch(sql: str) -> list[dict]:
        with my.cursor() as c:
            c.execute(sql)
            return list(c.fetchall())

    # —— 读源（建立 id→member 映射，逐级向上解析 go_getter） ——
    gg_ids = {r["id"] for r in fetch("SELECT id FROM go_getters")}
    member_of_gg = {gid: _member(gid) for gid in gg_ids}

    targets = fetch("SELECT id, go_getter_id, title, subject FROM targets")
    member_of_target = {t["id"]: member_of_gg[t["go_getter_id"]] for t in targets}

    plans = fetch("SELECT id, target_id, title FROM plans")
    member_of_plan = {p["id"]: member_of_target[p["target_id"]] for p in plans}

    milestones = fetch("SELECT id, plan_id, week_number, title FROM weekly_milestones")
    member_of_ms = {m["id"]: member_of_plan[m["plan_id"]] for m in milestones}

    tasks = fetch("SELECT id, milestone_id, title FROM tasks")
    member_of_task = {t["id"]: member_of_ms[t["milestone_id"]] for t in tasks}

    checkins = fetch("SELECT id, task_id, go_getter_id, status FROM check_ins")
    reports = fetch("SELECT id, go_getter_id, report_type, content_md FROM reports")

    # —— 全量重载到 PG（超级用户绕 RLS） ——
    with psycopg.connect(pg_dsn) as pg:
        with pg.cursor() as cur:
            cur.execute(
                "TRUNCATE report, check_in, task, weekly_milestone, plan, target "
                "RESTART IDENTITY CASCADE"
            )
            cur.executemany(
                "INSERT INTO target (id, family_member_id, title, subject) VALUES (%s,%s,%s,%s)",
                [(t["id"], member_of_target[t["id"]], t["title"], t.get("subject")) for t in targets],
            )
            cur.executemany(
                "INSERT INTO plan (id, family_member_id, target_id, title) VALUES (%s,%s,%s,%s)",
                [(p["id"], member_of_plan[p["id"]], p["target_id"], p["title"]) for p in plans],
            )
            cur.executemany(
                "INSERT INTO weekly_milestone (id, family_member_id, plan_id, week_number, title) "
                "VALUES (%s,%s,%s,%s,%s)",
                [(m["id"], member_of_ms[m["id"]], m["plan_id"], m["week_number"], m["title"])
                 for m in milestones],
            )
            cur.executemany(
                "INSERT INTO task (id, family_member_id, milestone_id, title) VALUES (%s,%s,%s,%s)",
                [(t["id"], member_of_task[t["id"]], t["milestone_id"], t["title"]) for t in tasks],
            )
            cur.executemany(
                "INSERT INTO check_in (id, family_member_id, task_id, status) VALUES (%s,%s,%s,%s)",
                [(c["id"], member_of_gg[c["go_getter_id"]], c["task_id"], c["status"]) for c in checkins],
            )
            cur.executemany(
                "INSERT INTO report (id, family_member_id, report_type, content_md) VALUES (%s,%s,%s,%s)",
                [(r["id"], member_of_gg[r["go_getter_id"]], r["report_type"], r["content_md"])
                 for r in reports],
            )
            # 显式插入 id 后修正序列，避免后续自增主键冲突
            for tbl in ("target", "plan", "weekly_milestone", "task", "check_in", "report"):
                cur.execute(
                    f"SELECT setval(pg_get_serial_sequence('{tbl}', 'id'), "
                    f"GREATEST((SELECT COALESCE(max(id), 0) FROM {tbl}), 1))"
                )
        pg.commit()

    my.close()
    print("[migrate_mariadb_to_pg] 搬迁完成（全量重载，幂等）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
