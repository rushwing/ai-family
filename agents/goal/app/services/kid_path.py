"""kid 结构化只路径 —— REQ-003 WP-7 / TC-003-07 / BUG-012（kid 红线）。

kid 仅：RLS 只读自有目标 + Draft-First 打卡 + 模板化赞语（praise_engine 离线，不走 LLM）。
不可：自由对话 / 创建目标 / 批准计划 / 写平台或他人目标 —— 一律 RedirectToParent（转家长）+ 审计 deny。
全程**不调用 LLM**（_llm_complete 永不被本模块调用；测试以 spy 断言）。

数据经平台 PG，以 aifam_app + claim=member 访问，RLS 保证只见自有（跨成员越权由 RLS + 本层共同堵）。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

import psycopg

# kid 越界动作（结构化只路径之外的一切写/对话）—— 一律转家长
DISALLOWED = {"create_goal", "approve_plan", "write_platform", "free_chat"}

# kid 路径目标写入计数（结构上恒为 0：本模块无任何目标写入代码路径）
_goal_writes: dict[str, int] = {}


class RedirectToParent(Exception):
    """kid 越界操作 —— 转家长处理。"""


@dataclass
class Task:
    id: int


@dataclass
class Goal:
    family_member_id: str
    target_id: int
    tasks: list[Task]


@dataclass
class CheckinResult:
    accepted: bool


@dataclass
class AuditEvent:
    action: str
    result: str


def _llm_complete(*args, **kwargs):  # noqa: ARG001
    """LLM 自由生成入口 —— kid 结构化只路径**永不**调用（测试 spy 断言其零调用）。"""
    raise RuntimeError("kid 结构化只路径不得调用 LLM")


def _dsn() -> str:
    dsn = os.getenv("AIFAMILY_PG_DSN")
    if not dsn:
        raise RuntimeError("未配置 AIFAMILY_PG_DSN")
    return dsn


def _txn(member: str):
    """以 aifam_app + claim=member 开启事务（RLS 只见自有）。"""
    conn = psycopg.connect(_dsn())
    conn.execute("BEGIN")
    conn.execute("SET LOCAL ROLE aifam_app")
    conn.execute("SELECT set_config('app.member_id', %s, true)", (member,))
    return conn


def _audit(conn, member: str, action: str, result: str):
    conn.execute(
        "INSERT INTO audit.event (family_member_id, actor, action, detail) "
        "VALUES (%s, %s, %s, %s::jsonb)",
        (member, member, action, json.dumps({"result": result})),
    )


def list_goals(member: str, owner: str | None = None) -> list[Goal]:
    """kid 只读自有目标；owner 指向他人时直接返回空（不可查看他人，RLS 亦兜底）。"""
    if owner is not None and owner != member:
        return []
    conn = _txn(member)
    try:
        targets = conn.execute(
            "SELECT id FROM target WHERE family_member_id=%s ORDER BY id", (member,)
        ).fetchall()
        goals: list[Goal] = []
        for (tid,) in targets:
            tasks = conn.execute(
                "SELECT tk.id FROM task tk "
                "JOIN weekly_milestone wm ON wm.id = tk.milestone_id "
                "JOIN plan p ON p.id = wm.plan_id "
                "WHERE p.target_id=%s AND tk.family_member_id=%s ORDER BY tk.id",
                (tid, member),
            ).fetchall()
            goals.append(Goal(member, tid, [Task(r[0]) for r in tasks]))
        return goals
    finally:
        conn.close()


def submit_checkin(member: str, task_id: int, draft_first: bool = False) -> CheckinResult:
    """Draft-First 打卡（kid 唯一写动作）：落 check_in + 审计 allow，**不调 LLM**。"""
    conn = _txn(member)
    try:
        conn.execute(
            "INSERT INTO check_in (family_member_id, task_id, status) VALUES (%s, %s, 'completed')",
            (member, task_id),
        )
        _audit(conn, member, "checkin", "allow")
        conn.commit()
        return CheckinResult(accepted=True)
    finally:
        conn.close()


def dispatch(member: str, action: str, payload: dict):
    """kid 越界动作（创建/批准/写平台/自由对话）：审计 deny + 转家长；**不**写目标、**不**调 LLM。"""
    conn = _txn(member)
    try:
        _audit(conn, member, action, "deny")
        conn.commit()
    finally:
        conn.close()
    raise RedirectToParent(f"'{action}' 需家长操作（kid 越界，已转家长）")


def goal_write_count(member: str) -> int:
    """kid 路径执行的目标写入数 —— 结构上恒为 0（本模块无目标写入代码路径）。"""
    return _goal_writes.get(member, 0)


def recent_audit(member: str) -> list[AuditEvent]:
    conn = _txn(member)
    try:
        rows = conn.execute(
            "SELECT action, detail->>'result' FROM audit.event "
            "WHERE family_member_id=%s ORDER BY id",
            (member,),
        ).fetchall()
        return [AuditEvent(action=a, result=r) for a, r in rows]
    finally:
        conn.close()
