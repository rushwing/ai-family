# GitHub Project 与 Harness

## 分工

GitHub Project 管理目标、日期、Release 和组合进度。Harness 管理正式工程需求、测试、缺陷、owner 和生命周期门禁。

```text
PRD / requirements.xlsx / roadmap.yaml
                │
                ▼ human-001 批准 Story
          Harness REQ-NNN
                │
                ├── TC-NNN-SS
                ├── BUG-NNN
                └── PR / CI / Release / trace_id
                │
                ▼ 单向同步
        GitHub 镜像 Issue / Project
```

## 产品层级

```text
Roadmap Goal
└── Epic
    └── Story / REQ
        └── Task（只在需要持久协作时创建）

Release：独立时间维度
Iteration：开发时间盒
```

Roadmap 不是 Epic 的别名，Release/Phase 也不作为父子层级。

## 权威字段

| 字段 | 权威来源 | GitHub 行为 |
|---|---|---|
| 产品范围、非目标 | PRD | 只链接，不复制 |
| Roadmap/Epic/Story 基线 | Excel + `roadmap.yaml` | 创建轻量镜像项 |
| REQ 描述、验收标准 | Harness | Issue 正文显示摘要和文件链接 |
| lifecycle status | Harness | Project Status 单向镜像 |
| owner | Harness | 可映射为 Assignee/Owner Role，不反写 |
| TC/BUG 门禁 | Harness/CI | Project 只显示 Blocked |
| Start/Target Date | GitHub Project | GitHub 权威 |
| Release | GitHub Milestone | Harness 保留 phase 映射 |
| 项目 On track/At risk | GitHub Project update | GitHub 权威 |
| 运行证据 | Langfuse/Audit | Issue/REQ 仅保存链接 |

## 镜像 Issue

只有满足下列任一条件时创建 Issue：

- Roadmap Goal 或 Epic 需要出现在 Project；
- Story 已经由 `human-001` 批准并创建正式 REQ；
- 外部反馈或生产问题需要进入收件箱；
- Task 跨人、跨会话、持续多日或阻塞其他工作。

Issue 标题保留稳定 ID：

```text
[REQ-011] 知微 Handover 与项目治理落盘
```

Issue 正文首段固定为：

```markdown
> Canonical source: harness/tasks/features/REQ-011.md
> 本 Issue 用于 Project 展示与讨论。状态和验收标准以 Harness 为准。
```

重要评论必须通过 PR 回写 REQ、BUG 或 ADR，不能只留在评论中。

## 状态映射

| Harness | Project Status |
|---|---|
| `draft` | Draft |
| `req_review`、`tc_design`、`tc_review` | Design & Test |
| `tc_impl`、`req_impl` | In Progress |
| `tc_impl_review`、`req_impl_review` | Review |
| `pr_draft` | Ready to Merge |
| `blocked` | Blocked |
| `done` | Done，关闭镜像 Issue |

同步方向固定为 `Harness → GitHub`。GitHub 的拖拽或字段编辑不得推进 Harness 状态机。

## Project 视图

声明式定义位于 `.github/project-management/home-intelligence.yaml`。

建议视图：

1. **产品 Roadmap**：Roadmap layout，只看 Epic，按 Roadmap Goal 分组；
2. **当前 Release**：Table layout，按 Epic 分组；
3. **交付看板**：Board layout，只看 Story/REQ，以 Status 为列；
4. **Epic 进度**：显示 Parent 和 Sub-issue Progress；
5. **Agent 队列**：按 Owner Role 分组；
6. **风险与阻塞**：只看 High Risk 或 Blocked。

## 物化时机

本 PR 只提交可评审的配置和权威文件，不在合并前创建外部 Project、Milestone 或镜像 Issue。

合并后由 `human-001` 或获授权的 Agent：

1. 创建 organization/user Project；
2. 创建 P0–P4 Milestone；
3. 创建 Roadmap/Epic 镜像 Issue；
4. 只为正式 Harness REQ 创建 Story Issue；
5. 配置 GitHub Action 或 MCP 同步；
6. 先以 read-only/dry-run 验证映射，再允许写入。

参考：

- <https://docs.github.com/en/issues/planning-and-tracking-with-projects/customizing-views-in-your-project/customizing-the-roadmap-layout>
- <https://docs.github.com/en/issues/planning-and-tracking-with-projects/understanding-fields>
- <https://docs.github.com/en/issues/using-labels-and-milestones-to-track-work/about-milestones>
- <https://github.com/github/github-mcp-server>
