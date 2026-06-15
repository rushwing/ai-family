# governance/ —— 安全 / 合规策略（受控边界 · 目录起步）

🔴 **kid 安全红线的源码权限映射**：任何触及 kid 安全策略 / Compliance 规则 / RLS / 审计 schema
的改动必须落在此边界内，受 CODEOWNERS 双签保护；策略以**版本化 bundle 只读下发**给 Agent/Compliance 消费——
Agent 改动无法绕过或反向篡改策略（"策略在引擎不在 prompt"，04 P6 / 03 §4 / ADR-013）。

- **先目录后独立仓**：单人初期用本目录 + CODEOWNERS；**kid 上线（M3）前升格为 `ai-family-governance` 独立仓**评估（ADR-013 Revisit Trigger）。
- M1 GoalAgent kid 走结构化只路径（无未审 LLM 输出给 kid），完整 Compliance v0 顺延 M3（BUG-012 / 08 §3）。

> 占位骨架；策略 bundle 随 M3 Compliance 落地。
