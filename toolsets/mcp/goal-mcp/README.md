# toolsets/mcp/goal-mcp —— GoalAgent MCP server

承接 goal-agent 的 36 tools / 6 组（admin/checkin/plan/report/tracks/wizard）。
迁移期从 `agents/goal/app/mcp/` 抽出为独立 MCP server；每个 write 类 tool 补 risk 元数据 + 工具侧 JWT，
无 auth metadata / 无测试者拒绝注册（tool manifest 见 [08 §6](../../../docs/design/08-goalagent-architecture.html)，ADR-010 / REQ-004）。

## M1（REQ-003 WP-4）已落地

`goal_mcp` 包 = 36 个 tool 的**逐 tool manifest 单一真值**（risk / 角色 / tenant scope /
两段式 / confirm 来源 / 工具侧 auth / 测试引用），与网关、agent 侧 `app/auth/oidc.py` 的
TOOL_POLICY 同源对齐。

- `goal_mcp.tool_registry()` —— 构建含 36 tool 的注册表（注册即校验契约）
- `goal_mcp.RegistrationError` —— 违反契约（写误标 read / 缺 auth / 缺 test_ref / 非两段式 /
  confirm 非用户来源）时抛出（BUG-017）
- `goal_mcp.fixture_tool(...)` —— 构造注册门禁负例
- M1 按 docs/design/08 defer 移除 `get_wizard_sources`（37 → 36）

验证（无需外部服务）：

```bash
cd toolsets/mcp/goal-mcp
python -m pytest tests/ -q          # TC-003-04(A) test_goal_manifest
```

> 网关写边界 / JWT 边界（TC-003-04B / TC-003-02B）为 env-gated，见 `../gateway`。
