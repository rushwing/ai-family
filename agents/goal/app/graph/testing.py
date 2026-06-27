"""图崩溃恢复测试夹具 —— REQ-003 WP-3 / TC-003-03（BUG-001）。

recovery_runner 以可注入确定性 idempotency_key 与故障点的方式驱动副作用执行，验证：
  * 业务提交后/checkpoint 前崩溃 → 重启不重复（恢复以 DB 业务状态为权威）；
  * 业务提交前崩溃 → 无可见状态，重放恰好一次；
  * 重复 cron 唤醒 / 并发投递 → idempotency_key 去重 → 副作用至多一次。

以超级用户连接（搬迁/恢复语义，绕 RLS）；用专用测试成员，cleanup 清理。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

import psycopg

from app.graph.side_effects import SimulatedCrash, deliver_outbox, execute_side_effect

_REPO = Path(__file__).resolve().parents[4]
_MIGRATIONS = _REPO / "data" / "migrations"
_TEST_MEMBER = "member-graph-test"


@dataclass
class Effects:
    business_writes: int
    outbox_intents: int
    external_deliveries: int
    score_writes: int


class _RecoveryRunner:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.member = _TEST_MEMBER
        self.threads: dict[str, dict] = {}
        self._ensure_schema()
        self._reset_member()

    # —— 基础设施 ——
    def _ensure_schema(self):
        migs = sorted(p for p in _MIGRATIONS.glob("*.sql") if p.name > "0001")
        with psycopg.connect(self.dsn, autocommit=True) as admin:
            for m in migs:
                admin.execute(m.read_text(encoding="utf-8"))

    def _reset_member(self):
        with psycopg.connect(self.dsn, autocommit=True) as admin:
            for tbl in ("graph_business", "graph_score", "graph_delivery", "outbox"):
                admin.execute(f"DELETE FROM {tbl} WHERE family_member_id=%s", (self.member,))

    def _conn(self):
        return psycopg.connect(self.dsn)  # 非 autocommit → 支持 conn.transaction()

    # —— 驱动 ——
    def start(self, node: str, idempotency_key: str) -> str:
        tid = uuid.uuid4().hex
        self.threads[tid] = {"node": node, "key": idempotency_key, "reconciled": False}
        return tid

    def kill_after_business_commit_before_checkpoint(self, tid: str):
        """业务写+outbox+idempotency 提交，但 checkpoint 未写（模拟此刻崩溃）。"""
        t = self.threads[tid]
        with self._conn() as c:
            execute_side_effect(c, node=t["node"], member=self.member, idempotency_key=t["key"])
        # 故意不写 checkpoint —— 崩溃点

    def kill_before_business_commit(self, tid: str):
        """业务事务提交前崩溃 → 回滚，无可见状态。"""
        t = self.threads[tid]
        with self._conn() as c:
            try:
                execute_side_effect(
                    c, node=t["node"], member=self.member, idempotency_key=t["key"],
                    fail_before_commit=True,
                )
            except SimulatedCrash:
                pass  # 事务已回滚

    def restart(self, tid: str):
        """恢复同一 thread：以 DB 业务状态为权威 reconcile，幂等重放 + 投递 + 写 checkpoint。"""
        t = self.threads[tid]
        with self._conn() as c:
            existing = c.execute(
                "SELECT 1 FROM graph_business WHERE family_member_id=%s AND idempotency_key=%s",
                (self.member, t["key"]),
            ).fetchone()
            # 恢复重放（幂等：已提交则 DO NOTHING）—— checkpoint 仅控制流，不覆盖业务状态
            execute_side_effect(c, node=t["node"], member=self.member, idempotency_key=t["key"])
            deliver_outbox(c, self.member)
            with c.transaction():
                c.execute(
                    "INSERT INTO lg_checkpoint (family_member_id, thread_id, checkpoint) "
                    "VALUES (%s, %s, %s)",
                    (self.member, tid, '{"step": "recovered"}'),
                )
            # 业务状态先于 checkpoint 存在 → 恢复以已提交业务状态为权威
            t["reconciled"] = existing is not None

    def deliver_cron_wakeup(self, tid: str, times: int = 1):
        """同一 cron 重复投递 times 次（同 idempotency_key）→ 去重。"""
        t = self.threads[tid]
        with self._conn() as c:
            for _ in range(times):
                execute_side_effect(c, node=t["node"], member=self.member, idempotency_key=t["key"])
                deliver_outbox(c, self.member)

    def deliver_concurrent(self, tid: str, times: int = 2):
        """同一图节点重复投递 times 次（UNIQUE(member, idempotency_key) 保证并发也去重）。"""
        t = self.threads[tid]
        for _ in range(times):
            with self._conn() as c:
                execute_side_effect(c, node=t["node"], member=self.member, idempotency_key=t["key"])
                deliver_outbox(c, self.member)

    # —— 观测 ——
    def effects(self, tid: str) -> Effects:
        key = self.threads[tid]["key"]
        with psycopg.connect(self.dsn, autocommit=True) as admin:
            def cnt(tbl):
                return admin.execute(
                    f"SELECT count(*) FROM {tbl} WHERE family_member_id=%s AND idempotency_key=%s",
                    (self.member, key),
                ).fetchone()[0]
            return Effects(
                business_writes=cnt("graph_business"),
                outbox_intents=cnt("outbox"),
                external_deliveries=cnt("graph_delivery"),
                score_writes=cnt("graph_score"),
            )

    def reconciled_from_business_state(self, tid: str) -> bool:
        return self.threads[tid]["reconciled"]

    def cleanup(self):
        self._reset_member()


def recovery_runner(dsn: str) -> _RecoveryRunner:
    return _RecoveryRunner(dsn)
