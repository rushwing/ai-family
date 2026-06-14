---
adr_id: ADR-010
title: "工具层架构：每域一个 FastMCP server + MCP 网关 + 工具侧鉴权 + Draft-First"
status: accepted
date: 2026-06-11
deciders: [human-001]
informed_by: []
supersedes: null
linked_reqs: [REQ-003]
---

## Context（背景与约束）

用户要求"一开始就做好 MCP/Tool Calling 的架构设计"。
既有资产：goal-agent 已有 FastMCP server（36 tools / 6 组）模式验证可行；travel_agent 有 MCP 集成层；
OpenClaw（MacMini）的 skills（web-search/calendar/email）需要桥接进平台。
reference.html 核心安全原则必须落位："**Agent 读到上下文 ≠ 用户拥有该权限**"——鉴权在工具侧，不在 Agent 侧。

## Options

### Option A: 每个领域 Agent 配套一个 FastMCP server，统一经 MCP 网关注册（选定）
**Pros:** 域内聚（工具与 Agent 同生命周期演进）；goal-agent 模式直接复用；网关给出统一的注册/白名单/审计切面
**Cons:** 网关是新增组件（可由轻量 FastAPI 服务实现，复杂度可控）

### Option B: 单一巨型 MCP server 承载全部工具
**Pros:** 部署最简
**Cons:** 所有域耦合在一个发布单元；工具白名单只能在 server 内部实现；违背按域演进

### Option C: 无网关，Agent 直连各 MCP server
**Pros:** 少一跳
**Cons:** 白名单/审计逻辑复制到每个 Agent；OpenClaw 桥接、未来第三方 MCP server 的信任边界无处安放

## Decision

三层结构：

```
LangGraph Agent ──(MCP client)──► MCP Gateway ──► 各域 FastMCP server / OpenClaw bridge / 第三方 MCP
```

约定全集：

1. **一域一 server**：goal-mcp、study-mcp、travel-mcp、stock-mcp、research-mcp、knowledge-mcp、data-mcp；
   平台工具（通知、文件）归 platform-mcp
2. **网关职责**：server 注册表（含工具 schema 版本）；按 `role` + `allowed_tools` claim 下发工具白名单
   （kid 看不到 stock-mcp 的存在，而非调用被拒）；JWT 透传与校验；每次调用写审计（trace_id、member、tool、参数摘要、结果状态）；
   第三方/OpenClaw 工具标记 `untrusted_output: true`，其返回内容进入上下文前过 Compliance 注入检测
3. **工具侧鉴权**：每个 tool 实现首行校验 JWT（网关透传原始 token），以用户身份连数据源
   （PG 连接设置 `app.current_member`，见 ADR-003）；工具绝不信任 Agent 传入的 member_id 参数
4. **风险分级与 Draft-First**：工具元数据声明 `risk: read | draft | write | high`；
   `write` 以上必须实现两段式：`prepare_xxx`（返回草稿+确认 token）→ `confirm_xxx`（带确认 token 执行）；
   确认动作只能来自 ChatUI 的用户显式点击（Planner 不能自我确认）
5. **OpenClaw 桥接**：MacMini 上的 OpenClaw skills 经其原生 MCP 能力暴露，网关注册为 `openclaw-*` 工具组，
   全部标记 untrusted_output；OpenClaw 自身凭证（日历/邮箱）只存在 MacMini 本地

## Trade-off

- 接受网关一跳延迟与一个自研轻组件（~数百行 FastAPI），换取白名单/审计/信任边界的单点实施
- 两段式写操作牺牲交互流畅度，换取"高风险动作永远有人类确认"的硬保证（家庭场景含未成年人，不妥协）

## Consequences

- 工具 schema 即契约：进 git、带版本、变更走 REQ；网关在 schema 不匹配时拒绝注册（防漂移）
- goal-agent 36 tools 迁移时补充 risk 元数据与 JWT 校验（REQ-003 差距清单项）
- 审计表（PG，ADR-012）成为"谁在什么时候让 AI 做了什么"的唯一权威记录

## Revisit Trigger

- MCP 协议官方推出网关/registry 标准实现且满足白名单与审计需求（评估替换自研网关）
- 工具调用 p95 延迟中网关占比 > 20%

## Review Notes

- [codex-005][2026-06-14] “每个 tool 首行校验 JWT”无共享 auth 库/强制中间件/注册门禁，会退化为作者自觉；36 个 goal tools 迁移漏一个即越权口 → 已立 REQ-004（工具侧鉴权做成 FastMCP decorator + 注册门禁：无 auth metadata 或无测试的 tool 拒绝注册）。human-001 裁决：accept（2026-06-14, REQ-004）
- [gemini-002][2026-06-14] 工具返回外部数据（网页/API）未过滤直入 LLM 上下文，提示注入可绕 output filter 破 kid 红线 → 已立 BUG-005（网关层强制 Input Sanitization 中间件）。Claude：本 ADR 约定 2 已有“untrusted_output 过 Compliance 注入检测”，G2 要求把它从约定升为强制中间件，采纳为强化。human-001 裁决：accept（2026-06-14, BUG-005）
- [gemini-反驳][2026-06-14] 强制反驳：单体内把本地函数包成 MCP server 再 HTTP/SSE 调，增加无谓序列化/网络错误面，直接 import 更稳更快。Claude：与本 ADR 网关“白名单/审计/信任边界单点实施”取舍冲突，记录待裁。human-001 裁决：reject——家庭场景时延非关键；平台能异步处理任务、家庭成员提交后可去做别的事、完成时收通知，正是搭建初衷；可维护性/可扩展性 > 复杂度与时延的适度增加，保留 MCP 架构
- [gemini-r2][2026-06-14] ① 06 状态图数据流绕过鉴权网关、图文不符 → BUG-009；② kid 压测：RAG 注入（检索网页夹带“忽略安全策略”）+ 输出过滤被 Base64 等编码绕过则红线破——强化 BUG-005（网关消毒须做指令/数据定界 + 输出分类器抗编码），并汇入 REQ-009 对抗测试集。human-001 裁决：accept（2026-06-14, BUG-009 + 强化 BUG-005 + REQ-009）
