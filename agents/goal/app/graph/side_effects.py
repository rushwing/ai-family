"""副作用精确一次执行 —— REQ-003 WP-3 / BUG-001·BUG-013（验收 #5）。

核心不变量：
  * **业务写 + outbox 意图 + 计分** 在**同一事务**提交，均带 idempotency_key；
    UNIQUE(family_member_id, idempotency_key) + ON CONFLICT DO NOTHING 保证二次执行去重。
  * checkpoint（lg_checkpoint）与业务事务**分离**，仅记控制流。
  * 投递 relay 读 outbox → 落 graph_delivery（同 UNIQUE）→ 外部投递至多一次。
  * 崩溃恢复以**已提交业务状态**为权威：idempotency_key 已在即视为完成，不重复写/投。

连接由调用方传入（psycopg3，非 autocommit，以支持 conn.transaction()）。
"""
from __future__ import annotations

import psycopg

SIDE_EFFECT_NODES = ("daily_plan", "evaluate", "send_reminder")


class SimulatedCrash(Exception):
    """测试用：在业务事务提交前注入崩溃（事务回滚，无可见状态）。"""


def execute_side_effect(
    conn: "psycopg.Connection",
    *,
    node: str,
    member: str,
    idempotency_key: str,
    fail_before_commit: bool = False,
) -> None:
    """在单一事务内幂等地施加节点副作用（业务写 + outbox + 可选计分）。

    fail_before_commit=True → 提交前抛 SimulatedCrash（回滚，不留可见业务状态）。
    """
    with conn.transaction():
        conn.execute(
            "INSERT INTO graph_business (family_member_id, idempotency_key, node) "
            "VALUES (%s, %s, %s) ON CONFLICT (family_member_id, idempotency_key) DO NOTHING",
            (member, idempotency_key, node),
        )
        conn.execute(
            "INSERT INTO outbox (family_member_id, idempotency_key, status) "
            "VALUES (%s, %s, 'pending') ON CONFLICT (family_member_id, idempotency_key) DO NOTHING",
            (member, idempotency_key),
        )
        if node == "evaluate":
            conn.execute(
                "INSERT INTO graph_score (family_member_id, idempotency_key, points) "
                "VALUES (%s, %s, 10) ON CONFLICT (family_member_id, idempotency_key) DO NOTHING",
                (member, idempotency_key),
            )
        if fail_before_commit:
            raise SimulatedCrash("crash before business commit")


def deliver_outbox(conn: "psycopg.Connection", member: str) -> int:
    """投递该成员 outbox 中 pending 意图；落 graph_delivery（至多一次）并标记 delivered。

    返回本次实际新增的外部投递条数。
    """
    pending = conn.execute(
        "SELECT idempotency_key FROM outbox WHERE family_member_id=%s AND status='pending'",
        (member,),
    ).fetchall()
    delivered = 0
    for (key,) in pending:
        with conn.transaction():
            row = conn.execute(
                "INSERT INTO graph_delivery (family_member_id, idempotency_key, channel) "
                "VALUES (%s, %s, 'notify') "
                "ON CONFLICT (family_member_id, idempotency_key) DO NOTHING RETURNING id",
                (member, key),
            ).fetchone()
            conn.execute(
                "UPDATE outbox SET status='delivered' WHERE family_member_id=%s AND idempotency_key=%s",
                (member, key),
            )
        if row is not None:
            delivered += 1
    return delivered
