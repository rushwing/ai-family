"""agent-core 长程图（LangGraph）—— REQ-003 WP-3。

主长程图：goal → milestone → daily_plan → check_in 循环（+ evaluate 计分 / send_reminder 通知）。
副作用节点的精确一次语义（业务写+outbox+idempotency_key 同一事务、checkpoint 仅控制流、
恢复以 DB 业务状态权威 reconcile）见 app.graph.side_effects（BUG-001/013）。

PG checkpointer / APScheduler→图唤醒入口在运行时注入（compose 起服务后接入）。
故障注入与恢复语义的回归夹具见 app.graph.testing（TC-003-03）。
"""
from __future__ import annotations

from typing import TypedDict

from app.graph.side_effects import (
    SIDE_EFFECT_NODES,
    SimulatedCrash,
    deliver_outbox,
    execute_side_effect,
)

__all__ = [
    "SIDE_EFFECT_NODES",
    "SimulatedCrash",
    "deliver_outbox",
    "execute_side_effect",
    "build_graph",
    "GoalState",
]


class GoalState(TypedDict, total=False):
    family_member_id: str
    goal_id: int
    idempotency_key: str
    step: str


def build_graph(checkpointer=None):
    """构建主长程图（控制流骨架）。checkpointer 由运行时注入（PG）。

    懒加载 langgraph，避免 `import app.graph` 时的硬依赖；节点业务逻辑随后续切片增量落地，
    副作用统一经 app.graph.side_effects 保证幂等。
    """
    from langgraph.graph import END, START, StateGraph

    g = StateGraph(GoalState)

    def _passthrough(step: str):
        def _node(state: GoalState) -> GoalState:
            return {**state, "step": step}
        return _node

    for node in ("goal", "milestone", "daily_plan", "check_in", "evaluate", "send_reminder"):
        g.add_node(node, _passthrough(node))

    g.add_edge(START, "goal")
    g.add_edge("goal", "milestone")
    g.add_edge("milestone", "daily_plan")
    g.add_edge("daily_plan", "check_in")
    g.add_edge("check_in", "evaluate")
    g.add_edge("evaluate", "send_reminder")
    g.add_edge("send_reminder", END)

    return g.compile(checkpointer=checkpointer)
