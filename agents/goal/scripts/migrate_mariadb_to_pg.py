#!/usr/bin/env python3
"""MariaDB(goal-agent) → PostgreSQL 16 数据搬迁（REQ-003 WP-1 / TC-003-01）。

设计要点：
  * **无损**：逐表搬迁全部业务字段（描述/日期/优先级/XP·streak/打卡详情/报告周期等），
    不丢字段。
  * **幂等且非破坏**：按主键 UPSERT（ON CONFLICT (id) DO UPDATE），**不 TRUNCATE**；
    二次执行结果一致（计数 / 业务键 / 关联不变），不重复也不丢已有数据。
  * **保留源主键**：以源 id 显式 UPSERT，维持 target↔plan↔milestone↔task↔check_in 关系。
  * **成员归属 + 跨租户隔离**：go_getter → family_member_id 映射；复合外键
    (family_member_id, parent_id) 在 DB 层保证父子同租户（见 0002）。
  * 目标库以**超级用户**连接（AIFAMILY_PG_DSN），搬迁期绕 RLS 直写。

env：AIFAMILY_MARIADB_DSN（源）、AIFAMILY_PG_DSN（目标，超级用户）。
注：data/migrations/0002 的 schema 须先应用。本脚本只搬数据。
"""
from __future__ import annotations

import os
import sys
import urllib.parse as up


def _member(go_getter_id: int) -> str:
    return f"member-go-{go_getter_id}"


def _mysql(dsn: str):
    import pymysql

    u = up.urlparse(dsn)
    return pymysql.connect(
        host=u.hostname, port=u.port or 3306, user=u.username,
        password=u.password or "", database=u.path.lstrip("/"),
        cursorclass=pymysql.cursors.DictCursor,
    )


def _upsert(cur, table: str, cols: list[str], rows: list[tuple]):
    if not rows:
        return
    placeholders = "(" + ", ".join(["%s"] * len(cols)) + ")"
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c != "id")
    cur.executemany(
        f"INSERT INTO {table} ({', '.join(cols)}) VALUES {placeholders} "
        f"ON CONFLICT (id) DO UPDATE SET {updates}",
        rows,
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

    go_getters = fetch(
        "SELECT id, display_name, grade, xp_total, streak_current, streak_longest, "
        "streak_last_date, is_active FROM go_getters"
    )
    member_of_gg = {g["id"]: _member(g["id"]) for g in go_getters}

    targets = fetch(
        "SELECT id, go_getter_id, title, subject, description, vacation_type, vacation_year, "
        "priority, status, subcategory_id, group_id, created_at FROM targets"
    )
    member_of_target = {t["id"]: member_of_gg[t["go_getter_id"]] for t in targets}

    plans = fetch(
        "SELECT id, target_id, title, overview, start_date, end_date, total_weeks, status, "
        "version, created_at FROM plans"
    )
    member_of_plan = {p["id"]: member_of_target[p["target_id"]] for p in plans}

    milestones = fetch(
        "SELECT id, plan_id, week_number, title, description, start_date, end_date, "
        "total_tasks, completed_tasks FROM weekly_milestones"
    )
    member_of_ms = {m["id"]: member_of_plan[m["plan_id"]] for m in milestones}

    tasks = fetch(
        "SELECT id, milestone_id, day_of_week, sequence_in_day, title, description, "
        "estimated_minutes, xp_reward, task_type, is_optional, status FROM tasks"
    )
    member_of_task = {t["id"]: member_of_ms[t["milestone_id"]] for t in tasks}

    checkins = fetch(
        "SELECT id, task_id, go_getter_id, status, mood_score, duration_minutes, notes, "
        "xp_earned, streak_at_checkin, praise_message, skip_reason, created_at FROM check_ins"
    )
    reports = fetch(
        "SELECT id, go_getter_id, report_type, period_start, period_end, content_md, "
        "tasks_total, tasks_completed, tasks_skipped, xp_earned FROM reports"
    )

    with psycopg.connect(pg_dsn) as pg:
        with pg.cursor() as cur:
            _upsert(cur, "go_getter",
                ["id", "family_member_id", "display_name", "grade", "xp_total",
                 "streak_current", "streak_longest", "streak_last_date", "is_active"],
                [(g["id"], member_of_gg[g["id"]], g["display_name"], g["grade"], g["xp_total"],
                  g["streak_current"], g["streak_longest"], g["streak_last_date"],
                  bool(g["is_active"])) for g in go_getters])

            _upsert(cur, "target",
                ["id", "family_member_id", "title", "subject", "description", "vacation_type",
                 "vacation_year", "priority", "status", "subcategory_id", "group_id", "created_at"],
                [(t["id"], member_of_target[t["id"]], t["title"], t["subject"], t["description"],
                  t["vacation_type"], t["vacation_year"], t["priority"], t["status"],
                  t["subcategory_id"], t["group_id"], t["created_at"]) for t in targets])

            _upsert(cur, "plan",
                ["id", "family_member_id", "target_id", "title", "overview", "start_date",
                 "end_date", "total_weeks", "status", "version", "created_at"],
                [(p["id"], member_of_plan[p["id"]], p["target_id"], p["title"], p["overview"],
                  p["start_date"], p["end_date"], p["total_weeks"], p["status"], p["version"],
                  p["created_at"]) for p in plans])

            _upsert(cur, "weekly_milestone",
                ["id", "family_member_id", "plan_id", "week_number", "title", "description",
                 "start_date", "end_date", "total_tasks", "completed_tasks"],
                [(m["id"], member_of_ms[m["id"]], m["plan_id"], m["week_number"], m["title"],
                  m["description"], m["start_date"], m["end_date"], m["total_tasks"],
                  m["completed_tasks"]) for m in milestones])

            _upsert(cur, "task",
                ["id", "family_member_id", "milestone_id", "day_of_week", "sequence_in_day",
                 "title", "description", "estimated_minutes", "xp_reward", "task_type",
                 "is_optional", "status"],
                [(t["id"], member_of_task[t["id"]], t["milestone_id"], t["day_of_week"],
                  t["sequence_in_day"], t["title"], t["description"], t["estimated_minutes"],
                  t["xp_reward"], t["task_type"], bool(t["is_optional"]), t["status"])
                 for t in tasks])

            _upsert(cur, "check_in",
                ["id", "family_member_id", "task_id", "status", "mood_score", "duration_minutes",
                 "notes", "xp_earned", "streak_at_checkin", "praise_message", "skip_reason",
                 "created_at"],
                [(c["id"], member_of_gg[c["go_getter_id"]], c["task_id"], c["status"],
                  c["mood_score"], c["duration_minutes"], c["notes"], c["xp_earned"],
                  c["streak_at_checkin"], c["praise_message"], c["skip_reason"], c["created_at"])
                 for c in checkins])

            _upsert(cur, "report",
                ["id", "family_member_id", "report_type", "period_start", "period_end",
                 "content_md", "tasks_total", "tasks_completed", "tasks_skipped", "xp_earned"],
                [(r["id"], member_of_gg[r["go_getter_id"]], r["report_type"], r["period_start"],
                  r["period_end"], r["content_md"], r["tasks_total"], r["tasks_completed"],
                  r["tasks_skipped"], r["xp_earned"]) for r in reports])

            # 显式插入 id 后修正序列，避免后续自增主键冲突
            for tbl in ("go_getter", "target", "plan", "weekly_milestone", "task",
                        "check_in", "report"):
                cur.execute(
                    f"SELECT setval(pg_get_serial_sequence('{tbl}', 'id'), "
                    f"GREATEST((SELECT COALESCE(max(id), 0) FROM {tbl}), 1))"
                )
        pg.commit()

    my.close()
    print("[migrate_mariadb_to_pg] 搬迁完成（全字段无损 · UPSERT 幂等 · 非破坏）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
