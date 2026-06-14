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

`proposed →（human-001 批准 + 评审闭环 gate）→ accepted →（被新 ADR 替代）→ superseded`

用户已口头拍板的决策直接以 `accepted` 入库，但仍开放 Review Notes 接受评审挑战。

### 4.1 评审闭环 Gate（proposed → accepted 前置条件）

一个 ADR 置为 `accepted` 前必须同时满足（缺一不可）：

1. **informed_by 完整**：所有产生过评审意见的来源 UID 已记入 frontmatter `informed_by`；
2. **Review Notes 全裁决**：`## Review Notes` 段每条意见都带 `→ human-001 裁决` 结论，无悬空未裁意见。合法处置：`accept` / `reject` / `转 BUG` / `转 REQ` / `defer`（明确延迟决策——须同时落一条 Revisit Trigger，注明何时/凭什么再决，`defer` 视为已裁决，不算悬空）；
3. **决策一致性缺陷全闭**：由本 ADR 引出、**会改变决策本身**的缺陷（设计图↔决策不符、决策内部矛盾等，典型 BUG-008）必须 `resolved`/`closed`。**实现加固类缺陷不在此列**——凡带 `linked_req` 指向下游实现期 REQ 的 BUG（如 RLS 加固 BUG-002、幂等 BUG-001），属"决策已定、实现期加固"，由其 `linked_req` 阻塞**对应 REQ 的 `done`**，**不**回头阻塞本 ADR 的 `accepted`；
4. **决策与设计稿一致**：裁决若改动了决策，正文 Decision/Trade-off 已同步更新（不得只记在 Review Notes）。

未满足上述任一条的 ADR 必须停留在 `proposed`。注意阻塞方向：gate 失败阻塞的是**本 ADR 自身的 `accepted`**；实现加固缺陷阻塞的是**下游 REQ 的 `done`**——两者不互相串扰（架构决策不因实现期加固未完成而被打回）。

### 4.2 一致性检查（CI / 评审脚本）

校验脚本对 `docs/adr/*.md` 扫描，任一 `status: accepted` 的 ADR 若存在以下任一即判失败：① 未裁决 Review Notes 条目（`defer` 不算未裁决，但缺对应 Revisit Trigger 的 `defer` 判失败）；② `informed_by` 为空但 Review Notes 非空；③ **决策一致性类**关联 BUG 仍 open/in_progress（带 `linked_req` 的实现加固 BUG 不计入本检查，改由下游 REQ 的 `done` 门禁覆盖）。该检查纳入 REQ-001 验收（设计稿定稿门禁）。
