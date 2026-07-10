"""goal_mcp —— GoalAgent MCP server 的 manifest 契约与注册门禁（REQ-003 WP-4）。

公共 API（供 TC-003-04 / 网关消费）：
    tool_registry()   -> ToolRegistry（含 36 个 tool，注册即校验契约）
    RegistrationError -> 违反 manifest 契约时抛出（BUG-017）
    fixture_tool(...) -> 构造注册门禁负例用工具
    Tool / ToolRegistry / TOOL_SPEC / DEFERRED_TOOLS
"""
from goal_mcp.manifest import (
    DEFERRED_TOOLS,
    TOOL_SPEC,
    RegistrationError,
    Tool,
    ToolRegistry,
    fixture_tool,
    tool_registry,
)

__all__ = [
    "tool_registry",
    "RegistrationError",
    "fixture_tool",
    "Tool",
    "ToolRegistry",
    "TOOL_SPEC",
    "DEFERRED_TOOLS",
]
