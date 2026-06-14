# ADR Standard（架构决策记录规范）

> ADR 文件本体存放于 `docs/adr/`，本文件只定义规范。

## 1. 命名与编号

- 路径：`docs/adr/ADR-NNN-<kebab-case-slug>.md`，NNN 零填充三位顺序号
- 一个 ADR 只记录一个决策；推翻旧决策时**新增 ADR** 并将旧 ADR 置 `superseded`，不得原地改写历史

## 2. Frontmatter

```yaml
---
adr_id: ADR-004
title: "向量检索底座：Elasticsearch vs pgvector"
status: accepted    # proposed | accepted | superseded | deprecated
date: 2026-06-11
deciders: [human-001]
informed_by: []     # 评审来源，如 [codex-review-001]
supersedes: null    # 被替代的 ADR 编号
linked_reqs: []
---
```

## 3. 正文结构（必须完整，显性化思考过程）

```markdown
## Context（背景与约束）
为什么现在必须做这个决策；硬约束（硬件/预算/技能栈/合规）。

## Options（候选项，每项含 Pros / Cons）
### Option A: xxx
**Pros:** ... / **Cons:** ...
（至少两个候选项；"什么都不做"算合法候选项）

## Decision（决策）
选了哪个，一句话。

## Trade-off（明确放弃了什么）
选择 A 意味着放弃 B 的哪些好处、接受 A 的哪些坏处。这一段不许空着。

## Consequences（影响）
对部署、代码结构、运维、后续决策的连锁影响。

## Revisit Trigger（重审触发条件）
满足什么可观测条件时必须重新评估本决策（规模阈值/性能阈值/成本阈值/生态变化）。

## Review Notes（评审追加区）
Codex/Gemini 评审意见追加在此，格式：`- [UID][日期] 意见原文 → human-001 裁决`
```

## 4. 状态流转

`proposed →（human-001 批准）→ accepted →（被新 ADR 替代）→ superseded`

用户已口头拍板的决策直接以 `accepted` 入库，但仍开放 Review Notes 接受评审挑战。
