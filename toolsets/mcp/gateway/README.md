# toolsets/mcp/gateway —— MCP 网关（信任边界）

请求验签 · 工具白名单 · 工具侧 JWT 校验 · write 类 risk 两段式 · 审计（ADR-010）。
所有工具调用唯一入口；确认令牌仅来自 ChatUI 用户点击、网关校验来源，Agent/Planner 不能自我确认。

> M1：随 REQ-003 切片 + REQ-004（注册门禁）落地。占位骨架。
