---
adr_id: ADR-015
title: "被遗忘权与审计不可变性的协调（删除策略 + 未成年人监护优先）"
status: proposed
date: 2026-06-14
deciders: [human-001]
informed_by: [gemini-review-001]
supersedes: null
linked_reqs: [REQ-008]
---

## Context（背景与约束）

两条需求直接冲突：
- **被遗忘权（REQ-008）**：租户 = 家庭成员，成员可要求删除其在 PG/pgvector/Neo4j/MinIO 的数据。
- **审计不可变（BUG-011）**：家长监护要求审计日志 append-only、不可被 kid 删除/软删除规避。

冲突点：删数据 vs 留审计。尤其**未成年人场景**——若 kid 的“删除请求”能抹掉记录，家长监护即失效；但若什么都不能删，被遗忘权落空。硬约束：kid 安全红线（P6）要求家长始终保有监护可见性；同时家庭信任模型下成人应能清理自己的数据。

## Options

### Option A: 硬删除全部（含审计）
**Pros:** 被遗忘权最彻底。
**Cons:** 违背 BUG-011 与家长监护；kid 可自抹痕迹——**否决**（破红线）。

### Option B: 永不删除，只匿名化
**Pros:** 审计完整。
**Cons:** 被遗忘权落空；高敏内容仍在库——**否决**。

### Option C: 内容删除/匿名化 + 审计 append-only 留最小元数据 + 未成年监护优先（选定）
**Pros:**
- **审计与内容分离**：审计只存“谁/何时/做了什么 + 内容指纹/引用”，**不存可删内容本体**；删除删的是内容本体（业务表/向量 chunk/图谱实体/对象存储），审计行保留但不泄露已删内容。
- **未成年监护优先**：kid 自身无权抹除监护审计链；kid 内容可删，但家长监护审计 append-only 不可删；删除请求由家长（监护人）确认。
- 成人自助：自助请求 → 四数据面级联删除/匿名化，审计保留最小元数据。
- 可选 **crypto-shredding**：高敏内容按成员密钥加密，删除 = 销毁密钥使数据不可恢复，审计引用仍在——兼顾“被遗忘”与“不可变审计”。
**Cons:** 审计永远留一条最小痕迹（非纯粹被遗忘）；crypto-shredding 引入密钥管理复杂度（设为可选）。

## Decision

采用 **Option C**：
1. **审计独立、append-only、只存元数据/指纹**（BUG-011）；删除操作本身也写一条审计（谁/何时/删除范围）。
2. **成人成员**：自助删除请求 → PG/pgvector/Neo4j/MinIO 四数据面级联删除或匿名化（REQ-008）；审计仅保留最小元数据。
3. **未成年人（kid）**：监护优先——kid 内容可删，但家长监护审计链不可删；任何 kid 删除请求经家长确认（Draft-First），kid 无权触达审计表。
4. **高敏内容可选 crypto-shredding**：以销毁密钥实现“事实不可恢复 + 审计引用保留”。

## Trade-off

接受“审计永远留一条最小痕迹”（牺牲纯粹意义的被遗忘），换取家长监护不可规避与防 kid 自抹；接受 crypto-shredding 的密钥管理成本（仅对高敏内容启用）。放弃 Option A 的彻底删除与 Option B 的零删除两个极端。

## Consequences

- REQ-008 据本 ADR 实现级联删除/匿名化与监护分支；BUG-011 的审计 schema 据本 ADR 只存元数据/指纹。
- 删除是高风险动作 → 走 Draft-First 两段式确认（ADR-010）；kid 删除路由到家长确认。
- 需定义“最小审计元数据”集合与“内容指纹”算法，进 GLOSSARY。
- 与 ADR-003（RLS）/ADR-012（审计权威）协同：审计表施 INSERT-only role。

## Revisit Trigger

- 出现真实法规要求（未成年人保护法 / GDPR 类）需收紧或改写删除语义。
- 家庭外用户接入（多租户 B2C 形态）使监护模型不再适用。

## Review Notes（评审追加区）

- [claude][2026-06-14] 本 ADR 为 human-001 指示起草（status: proposed），待裁决：① Option C 是否采纳；② crypto-shredding 设为可选/必选/不做；③ 成人匿名化 vs 硬删除的默认。
