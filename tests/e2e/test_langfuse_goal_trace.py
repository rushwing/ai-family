"""TC-003-08（B）：ChatUI→网关→agent-core→工具调用 的端到端 Langfuse trace 贯通。

需求 8 / 验收 #3；回归 BUG-018。

env-gated（REQ-002 范式）：缺 base_url / langfuse 时 skip；req_impl 起全栈后转 passing。
按唯一 trace_id 精确检索本次调用（避免取历史任意 trace 假绿，承 TC-002-09 教训）。
"""
import uuid

import pytest

from conftest import require

httpx = pytest.importorskip("httpx")


def _langfuse_client():
    pytest.importorskip("langfuse", reason="langfuse SDK 未安装")
    from langfuse import Langfuse

    require("langfuse")
    return Langfuse()


def test_chatui_to_tool_trace_is_complete():
    base = require("base_url")
    lf = _langfuse_client()
    trace_id = f"req003-{uuid.uuid4()}"

    # 经 ChatUI 后端发起一次需确认的目标写（携带唯一 trace_id）
    r = httpx.post(
        f"{base}/api/chat",
        json={"message": "建一个目标", "trace_id": trace_id, "confirm": True},
        timeout=30,
    )
    assert r.status_code == 200

    trace = lf.get_trace(trace_id)
    span_names = {s.name for s in trace.observations}
    # 四段贯通：ChatUI → MCP 网关 → agent-core → 工具调用
    assert {"chatui.request", "gateway", "agent-core", "tool.call"} <= span_names
    gen = next(o for o in trace.observations if o.type == "GENERATION")
    assert gen.usage and gen.usage.total_tokens is not None  # token
    assert gen.calculated_total_cost is not None  # 成本
    assert gen.latency is not None  # 延迟
