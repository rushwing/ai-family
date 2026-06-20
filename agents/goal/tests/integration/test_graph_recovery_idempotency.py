"""TC-003-03：LangGraph 崩溃恢复——业务状态权威与副作用幂等。

需求 3 / 验收 #2·#5；回归 BUG-001 / BUG-013。

env-gated：未设 AIFAMILY_PG_DSN 或 agent-core 图/outbox（WP-3）尚未落地时 skip；
req_impl 起 PG checkpointer + outbox 后转 passing。
"""
import os

import pytest

DSN = os.getenv("AIFAMILY_PG_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="设 AIFAMILY_PG_DSN 运行图恢复幂等用例")

# WP-3：主长程图 + 副作用/outbox + 故障注入测试夹具
graph = pytest.importorskip("app.graph", reason="agent-core 图未落地（WP-3）")
harness = pytest.importorskip("app.graph.testing", reason="图故障注入夹具未就绪（WP-3）")

SIDE_EFFECT_NODES = ["daily_plan", "evaluate", "send_reminder"]


@pytest.fixture
def runner():
    """提供可注入确定性 idempotency_key 与故障点的图运行器。"""
    r = harness.recovery_runner(dsn=DSN)
    yield r
    r.cleanup()


@pytest.mark.parametrize("node", SIDE_EFFECT_NODES)
def test_crash_after_business_commit_before_checkpoint(runner, node):
    """业务写+outbox+idempotency_key 已提交、checkpoint 未写时崩溃 → 重启不重复。"""
    thread = runner.start(node, idempotency_key=f"idem-{node}")
    runner.kill_after_business_commit_before_checkpoint(thread)
    runner.restart(thread)

    eff = runner.effects(thread)
    assert eff.business_writes == 1, f"{node}：重复写库"
    assert eff.outbox_intents == 1, f"{node}：重复 outbox 意图"
    assert eff.external_deliveries == 1, f"{node}：重复外部投递/通知"
    assert eff.score_writes <= 1, f"{node}：重复计分"
    # 恢复以已提交业务状态为权威，checkpoint 仅控制流
    assert runner.reconciled_from_business_state(thread)


@pytest.mark.parametrize("node", SIDE_EFFECT_NODES)
def test_crash_before_business_commit_leaves_no_visible_state(runner, node):
    thread = runner.start(node, idempotency_key=f"idem-pre-{node}")
    runner.kill_before_business_commit(thread)
    runner.restart(thread)

    eff = runner.effects(thread)
    assert eff.business_writes == 1, "未提交事务不应留下可见业务状态；重放后恰好一次"
    assert eff.external_deliveries <= 1


def test_duplicate_cron_wakeup_no_double_effect(runner):
    thread = runner.start("daily_plan", idempotency_key="idem-cron")
    runner.deliver_cron_wakeup(thread, times=2)  # 同一 cron 重复投递两次
    eff = runner.effects(thread)
    assert eff.business_writes == 1
    assert eff.external_deliveries == 1


def test_same_idempotency_key_dedup_on_concurrent_delivery(runner):
    thread = runner.start("send_reminder", idempotency_key="idem-dup")
    runner.deliver_concurrent(thread, times=2)  # 同一图节点并发投递两次
    eff = runner.effects(thread)
    assert eff.external_deliveries == 1, "同一 idempotency_key 二次执行须被去重"
