# Harness Engineering — 工程方法说明

> 约定承自 [rushwing/OpenStock](https://github.com/rushwing/OpenStock) 的 `harness/` 体系，适配本项目（设计先行、人机协作、多 AI 评审）。
> 术语以根目录 [GLOSSARY.md](../GLOSSARY.md) 为准。

## 1. 核心思想

所有工作项（需求、测试用例、缺陷、架构决策）都是**版本库内的 Markdown 文件**，带结构化 frontmatter 与显式生命周期状态。
人、Claude Code、Codex、Gemini 之间的协作通过**文件状态流转**完成交接（handoff），不依赖口头/会话记忆。

## 2. 目录与编号

```
harness/
├── requirement-standard.md   # REQ 规范
├── testcase-standard.md      # TC 规范
├── bug-standard.md           # BUG 规范
├── adr-standard.md           # ADR 规范（ADR 文件本体在 docs/adr/）
└── tasks/
    ├── features/     REQ-NNN.md        # 需求，零填充三位顺序号
    ├── test-cases/   TC-NNN-SS.md      # 用例，NNN 关联 REQ，SS 为用例序号
    ├── bugs/         BUG-NNN.md        # 缺陷
    └── archive/done/ REQ-NNN.md        # 完成项归档
```

## 3. 生命周期（REQ 主状态机）

```
draft → req_review ⇄ tc_design → tc_review ⇄ tc_impl → tc_impl_review
      → req_impl → req_impl_review → pr_draft → done
任意状态 →(被 BUG 阻塞)→ blocked →(BUG 关闭)→ 恢复原状态
```

M0（纯设计阶段）的 REQ 允许简化：`draft → req_review → done`，`tc_policy: exempt` 并注明豁免理由。

## 4. Handoff 协议（开工三检查）

任何执行者（人或 AI agent）开始一项工作前必须确认：

1. 对应 REQ 文件存在；
2. 自己与 REQ 的 `owner` 字段一致；
3. REQ 的 `status` 处于自己的合法工作状态。

本项目注册的执行者 UID：

| UID | 角色 | 合法工作状态 |
|---|---|---|
| `claude-code-001` | 设计/实现主力 | draft, tc_design, tc_impl, req_impl |
| `codex-review-001` | 架构/代码评审 | req_review, tc_review, req_impl_review |
| `gemini-review-001` | 架构/代码评审（第二视角） | req_review, req_impl_review |
| `human-001` | 决策与合并（用户本人） | 全部状态的最终裁决、PR 合并 |

## 5. 评审意见回流规则

Codex/Gemini 的评审产出**不直接改设计稿**，而是：

- 设计缺陷 → 提 `BUG-NNN`（`bug_type: req_bug`），关联对应 REQ；
- 新增诉求 → 提新 `REQ-NNN`（status: draft）；
- 选型异议 → 在对应 `ADR-NNN` 的 Review Notes 段落追加意见，由 human-001 裁决是否改决策。

**ADR 评审闭环 gate（BUG-006）**：选型异议记录后必须闭环——一个 ADR 置 `accepted` 前，须满足 `informed_by` 完整、Review Notes 每条均带 human-001 裁决（`defer` 须配 Revisit Trigger）、**决策一致性类**关联 BUG 全闭、决策变更已同步进正文（详见 [adr-standard.md §4.1](adr-standard.md)）。未闭环的 ADR 停留 `proposed` 自身的 `accepted` 被阻塞；而带 `linked_req` 的实现加固 BUG 不阻塞 ADR，只阻塞其下游 REQ 的 `done`。一致性检查纳入 REQ-001 验收。

## 6. 与 GoalAgent 的关系（dogfooding）

M1 起，本仓库的里程碑与 REQ 同步录入 GoalAgent 作为第一个正式 Goal（"ai-family 项目开发"），
GoalAgent 的日报/周报覆盖项目进度。在此之前以 `tasks/features/` 目录为唯一进度视图。
