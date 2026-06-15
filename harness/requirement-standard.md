# Requirement Standard（REQ 规范）

> 承自 OpenStock `harness/requirement-standard.md`，按本项目（设计先行 + 多 AI 评审）适配。

## 1. 文件位置与命名

- 路径：`harness/tasks/features/REQ-NNN.md`，NNN 为零填充三位顺序号（REQ-001、REQ-042）
- 完成后移入 `harness/tasks/archive/done/`
- 一个 REQ 只描述一个可独立验收的需求；过大需求拆分并用 `depends_on` 关联

## 2. Frontmatter 必填字段

```yaml
---
req_id: REQ-001
title: "一句话需求标题"
status: draft          # 见生命周期
owner: claude-code-001 # 注册 UID，见 harness/README.md
priority: P0           # P0–P3
phase: M0              # 里程碑代号，见 GLOSSARY §8
scope: design          # design | backend | frontend | fullstack | infra | docs | harness
tc_policy: required    # required | optional | exempt（exempt 必须写 exempt_reason）
exempt_reason: ""
depends_on: []         # [REQ-NNN, ...]
test_case_ref: []      # [TC-NNN-SS, ...]
acceptance: "一句话、现在时态、可验证的验收标准"
review_round: 0
pending_bugs: []       # 仅登记"评审打回本 REQ"的 BUG，非空即 blocked；BUG 的 linked_req 关联不进此处（见 §4）
pr_number: null
---
```

## 3. 正文结构

```markdown
## 背景
## 需求描述
## 非目标（明确不做什么，防 scope 外溢）
## 验收标准明细（可多条，每条满足"一句话/现在时/可验证"）
## 设计引用（关联 ADR / design 文档锚点）
## Bug History（被阻塞与解除的记录，自动追加）
```

## 4. 生命周期

```
draft → req_review ⇄ tc_design → tc_review ⇄ tc_impl → tc_impl_review
      → req_impl → req_impl_review → pr_draft → done
```

- 状态后退（⇄）仅由评审打回触发，打回必须附 BUG 或评审意见
- `pending_bugs` 非空时整体置 `blocked`，提交信息格式：`bug-block: REQ-NNN blocked by BUG-NNN`
- **`pending_bugs` 与 `linked_req` 是两套机制**：`pending_bugs` 仅登记**评审打回**本 REQ、使其后退/挂起的 BUG（→ blocked）；而 BUG 侧 `linked_req` 指向本 REQ 只是"该 BUG 由本 REQ 承载修复"的关联，**不**自动进 `pending_bugs`、**不**改变 REQ 生命周期状态（设计期 REQ 可照常 `draft`/`req_review`）。
- **done 前置门禁**：任一**未闭**（`status` 为 `open`/`in_progress`/`blocked` —— 凡非 `resolved`/`closed`）的 `req_bug`，其 `linked_req` 指向某 REQ 时，该 REQ **不得置 `done`**（关联 req_bug 须全部 `resolved`/`closed`）。即 `linked_req` 阻塞的是 `done`、不是中间状态；与 ADR 评审闭环 gate（adr-standard §4.1 规则 3）同源。
- **M0 设计类 REQ 简化路径**：`draft → req_review → done`，`tc_policy: exempt`，验收以评审闭环为准
- **谁来执行各状态**：每个生命周期状态由注册的 agent 承担——见 [agent-registry.yml](agent-registry.yml) 的 `handles`（Planner/Generator/Evaluator/human，规范见 [agent-standard.md](agent-standard.md)）。Generator 与 Evaluator 必须为不同身份（避免自夸偏置）。`owner`/裁决/修复记录以 role-UID 署名。

## 5. 验收标准写法

✅ `kid 角色请求被拒资源时，收到引导性回复且 audit 表新增一条 deny 记录`
❌ `儿童保护功能正常工作`（不可验证）

## 6. 开工三检查（Handoff Gate）

1. REQ 文件存在；2. 执行者 UID == `owner`；3. `status` 在执行者合法工作状态内。
三者任一不满足，不得动手；冲突上报 human-001。
