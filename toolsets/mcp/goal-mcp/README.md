# toolsets/mcp/goal-mcp —— GoalAgent FastMCP server

承接 goal-agent 的 36 tools / 6 组（admin/plan/check-in/report/tracks/wizard）。
迁移期从 `agents/goal/app/mcp/` 抽出为独立 MCP server；每个 write 类 tool 补 risk 元数据 + 工具侧 JWT，
无 auth metadata / 无测试者拒绝注册（tool manifest 见 [08 §6](../../../docs/design/08-goalagent-architecture.html)，ADR-010 / REQ-004）。

> M1：随 REQ-003 切片改造落地。占位骨架。
