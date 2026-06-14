# Bug Standard（BUG 规范）

> 承自 OpenStock `harness/bug-standard.md`。

## 1. 文件位置与命名

- 路径：`harness/tasks/bugs/BUG-NNN.md`，NNN 零填充三位顺序号

## 2. Frontmatter

```yaml
---
bug_id: BUG-001
title: "一句话缺陷标题"
bug_type: req_bug    # req_bug | tc_bug | impl_bug | ci_bug | user_bug
status: open         # open | in_progress | blocked | resolved | closed
severity: medium     # critical | high | medium | low
owner: unassigned
linked_req: REQ-NNN
regression_tc: []    # [TC-NNN-SS]，high/critical 关闭前必填
blocked_reason: ""
---
```

## 3. bug_type 说明

| 类型 | 含义 | 典型来源 |
|---|---|---|
| req_bug | 需求/设计本身的缺陷 | **Codex/Gemini 架构评审意见**、设计自相矛盾、术语漂移 |
| tc_bug | 用例错误 | 期望结果写错、用例与验收标准脱节 |
| impl_bug | 实现缺陷 | 功能/逻辑错误 |
| ci_bug | 流水线/环境问题 | 构建失败、测试环境抖动 |
| user_bug | 真实使用反馈 | 家庭成员使用中报告的问题 |

## 4. 生命周期与阻塞流程

- `open → in_progress → resolved → closed`；外部依赖等待时置 `blocked` 并填 `blocked_reason`。**`open`/`in_progress`/`blocked` 均属"未闭"**，均受下述 REQ done 门禁约束（仅 `resolved`/`closed` 算闭）。
- **两种"阻塞 REQ"路径**（与 [requirement-standard.md §4](requirement-standard.md) 对齐，勿混用）：
  - **评审打回**：评审某 REQ 时发现的缺陷使其后退/挂起 → BUG 与 REQ 文件同 commit 更新，提交信息 `bug-block: REQ-NNN blocked by BUG-NNN`，写入该 REQ 的 `pending_bugs`，REQ 整体置 `blocked`。
  - **linked_req 承载修复**：BUG 的 `linked_req` 指向"将修复它"的 REQ → **不**进 `pending_bugs`、**不**改 REQ 生命周期状态（设计期 REQ 可照常 `draft`/`req_review`），仅作为该 REQ 的 **done 前置门禁**（关联 req_bug 未全部 `resolved`/`closed` 前，REQ 不得 `done`）。
- **解除/闭环**：评审打回类——`pending_bugs` 全部 closed 后 REQ 恢复原状态与 owner，并在 REQ 的 Bug History 段记录始末；linked_req 类——BUG 置 `resolved`/`closed` 即解除其对关联 REQ 的 done 门禁。
- **回归要求**：severity 为 high/critical 的 BUG，关闭前必须在 `tasks/test-cases/` 新增回归 TC 并双向回填

## 5. 正文结构

```markdown
## 现象
## 复现步骤 / 评审原文（req_bug 粘贴评审意见原文与出处）
## 期望行为
## 根因分析
## 修复方案
```
