# 知微 Home Intelligence

知微是 `ai-family` 的家庭设备数字孪生与控制入口。它把空间、网络、设备能力、任务队列、家庭场景和 Agent 工作流放在同一个可治理的产品边界内。

当前交付是可交互前端原型与产品/工程基线，设备数据仍为演示数据，尚未连接真实家庭 MCP 服务。

## 阅读顺序

| 层级 | 文件 | 回答的问题 |
|---|---|---|
| L0 | [HANDOVER.md](HANDOVER.md) | 当前有什么、能运行到哪里、下一步是什么 |
| L1 | [PRD.md](PRD.md) | 产品目标、范围、交互和验收边界是什么 |
| L1 | [requirements.xlsx](requirements.xlsx) | Roadmap、Epic、Story、Task 的完整结构化基线是什么 |
| L2 | [roadmap.yaml](roadmap.yaml) | Agent 如何快速读取 Roadmap/Epic/Story 索引 |
| L2 | [ARCHITECTURE.md](ARCHITECTURE.md) | 前端如何接入 ai-family、MCP 和异步任务系统 |
| L2 | [PROJECT_MANAGEMENT.md](PROJECT_MANAGEMENT.md) | GitHub Project 与 Harness 如何分工 |
| L3 | [`harness/tasks/features/REQ-011.md`](../../../harness/tasks/features/REQ-011.md) | 本次 Handover 如何进入现有 Harness 生命周期 |

## 单一权威

不同信息只允许一个权威来源：

| 信息 | 权威来源 |
|---|---|
| 产品范围、非目标、交互规则 | `PRD.md` |
| 产品需求基线 | `requirements.xlsx` |
| Roadmap/Epic/Story 机器索引 | `roadmap.yaml`，与 Excel 同版本发布 |
| 已批准进入工程流的需求 | `harness/tasks/features/REQ-NNN.md` |
| 需求生命周期、owner、TC/BUG 门禁 | Harness frontmatter 与 CI |
| 目标日期、组合进度、Release 视图 | GitHub Project / Milestone，由 Harness 单向同步 |
| 实现与评审 | Pull Request / CI |
| 上线记录 | GitHub Release |
| 运行证据 | `trace_id`、Langfuse、审计日志 |

如果同一字段发生冲突，以表中的权威来源为准。GitHub 镜像 Issue 不得反向覆盖 Harness。

## 代码位置

- Web 原型：`apps/home-intelligence-web/`
- 平台与领域架构：`docs/design/`
- MCP 网关：`toolsets/mcp/gateway/`
- 产品需求与交接：本目录
- 工程需求、测试和缺陷：`harness/tasks/`

## 变更规则

1. 产品范围变化先更新 PRD 和需求基线。
2. Excel 变更必须同步更新 `roadmap.yaml` 的版本、统计和层级索引。
3. Story 只有满足 Definition of Ready 并经 `human-001` 批准后，才创建正式 REQ。
4. 架构选择变化先更新或新增 ADR。
5. GitHub Project 是管理视图，不承载独立的验收标准副本。
