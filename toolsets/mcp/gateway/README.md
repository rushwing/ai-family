# toolsets/mcp/gateway —— MCP 网关（信任边界）

请求验签 · 工具白名单 · 工具侧 JWT 校验 · write 类 risk 两段式 · 审计（ADR-010）。
所有工具调用唯一入口；确认令牌仅来自 ChatUI 用户点击、网关校验来源，Agent/Planner 不能自我确认。

## M1（REQ-003 WP-4）已落地

入口 `gateway.app:app`（FastAPI）。`/tools/{tool}` 单一入口执行：

1. **工具侧 OIDC JWT 验签**（缺 / 非 JWT / 篡改 → 401；旧 `X-Telegram-Chat-Id` header 非 JWT → 401）
2. **manifest 角色门禁**（取自 `goal_mcp` 契约；kid 不得写 create/approve 等 → 403）
3. **tenant scope**：body 显式 `family_member_id` ≠ 调用者 → 跨成员越权 403 + 审计
4. **write 类两段式**：`{"prepare": true}` 签发用户来源 confirm token；execute 须带网关签发、
   **成员+工具+payload 绑定、一次性** token，缺 / 伪造 / Agent 自生成 / 换成员 / 替换参数一律拒
5. **旧直连禁用**：GoalAgent 自身的 `/api/v1/*` 与 `/mcp/*` 默认返回 410；仅配置的内部网关令牌可进入
6. **审计**：deny/allow 均记录；admin 可查全量，adult/kid 只能查本人记录

工具的**功能分发**经 `create_app(executor=...)` 注入；真实分发到 goal-mcp FastMCP 随服务联调
在 req_impl_review 闭环。未注入 executor 的默认应用对工具请求返回 503，并在 `/readyz` 报未就绪，
不会伪造成功。当前内存 confirm/audit 仅用于单实例边界验证，已有 TTL/容量限制；PG 持久化仍是联调项。

## 测试与联调

```bash
# 无外部服务的 manifest / trust-boundary 回归
cd toolsets/mcp/gateway && pip install -e ../goal-mcp -e .[test]
pytest ../goal-mcp/tests tests -q

# 完整 TC-003-04B / TC-003-02B 还需 Keycloak 与已注入真实 executor 的应用实例
export AIFAMILY_OIDC_ISSUER=http://localhost:8081/realms/ai-family
export AIFAMILY_OIDC_AUD=ai-family-chatui
export AIFAMILY_GATEWAY_URL=http://localhost:8080
python -m pytest tests/ ../../../tests -q -k "goal_write_boundary or goal_jwt_boundary"
```

模块级 `gateway.app:app` 故意不带 executor，只用于验证 fail-closed/readiness，不可作为完整联调实例。
未设 `AIFAMILY_GATEWAY_URL` 时外部服务用例 skip（两段式评审：tc_impl 审代码名副其实，
真实 executor + Keycloak 真跑归 req_impl_review）。
