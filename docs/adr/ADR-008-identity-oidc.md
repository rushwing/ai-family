---
adr_id: ADR-008
title: "身份提供方（IdP）：Keycloak（Authentik / Zitadel 对比落选）"
status: proposed
date: 2026-06-11
deciders: [human-001]
informed_by: []
supersedes: null
linked_reqs: [REQ-002]
---

## Context（背景与约束）

身份是整条安全链的源头：CF Access → **IdP OIDC** → ChatUI 会话 → JWT → MCP 工具侧鉴权 → PG RLS。
需求：家庭成员账号（约 4–6 个）、admin/adult/kid 三角色、OIDC 标准签发（ChatUI、Langfuse、Grafana、CF Access 都消费）、
JWT claim 携带 `family_member_id` 与 `role`。宿主 Pi5（内存预算 ~1GB 以内为宜）。
这是"学习企业 IAM"的核心样本之一。

## Options

### Option A: Keycloak（选定，proposed）
**Pros:** 企业 IAM 事实标准（OIDC/SAML/联邦/细粒度授权全特性），学习迁移价值最高；文档与社区最厚；
26.x Quarkus 形态显著瘦身（实测 ~600–800MB 常驻，Pi5 ARM64 官方镜像可用）；自定义 claim/mapper 灵活，满足 family_member_id 注入
**Cons:** 仍是三者中最重；管理台概念繁多（realm/client/mapper），上手成本高；版本升级偶有迁移工作量

### Option B: Authentik
**Pros:** Python 技术栈（用户可读源码）、UI 现代、flow 编排灵活
**Cons:** Server+Worker+Redis+PG 多容器，总内存占用并不比 Keycloak 小；OIDC 之外的企业特性（authz services）弱；社区规模中等

### Option C: Zitadel
**Pros:** Go 单二进制最轻（~300MB），多租户原生，API-first
**Cons:** 生态与文档薄；自定义 claim 能力较绕；遇到问题可借鉴的资料最少——学习项目里"卡住没人问"是真实成本

## Decision

**Keycloak 26.x（单 realm `family`），部署于 Pi5，后端库复用 NAS PG。**

配置要点：
- 角色：realm roles `admin` / `adult` / `kid`；kid 账号禁用自助改密之外的自助功能
- Token：access token 含 `sub`（= family_member_id）、`role`、`allowed_tools` 组 claim；TTL 15min + refresh
- 下游 client：chatui（authorization code + PKCE）、langfuse、grafana、cf-access（OIDC 联邦）
- admin 控制台仅 Tailscale 内可达（ADR-007）

## Trade-off

- 接受三者中最高的资源占用与概念复杂度，换取企业标准特性全集 + 最高学习价值 + 最低"卡住"风险
- 放弃 Zitadel 的轻量——Keycloak（~800MB）由 618 到货的 Mac Mini M4（16GB 主运行时）承载，资源宽松；Pi5 4GB 已不承载运行时重组件（见 docs/design/02 §6 资源表）

## Consequences

- 所有服务的认证一律 OIDC 对接 IdP，**任何组件不得自建用户表**（ChatUI 的 user 表只存业务侧扩展属性，主键 = IdP sub）
- LiteLLM virtual key、Neo4j 工具过滤、RLS 会话变量全部以 `sub` 为锚
- IdP realm 配置导出 JSON 进配置库，重建可复现

## Revisit Trigger

- Mac Mini 内存水位持续 > 85% 且 Keycloak 是主要贡献者（评估换 Zitadel）
- 家庭外用户接入需求（多 realm / B2C 形态）

## Review Notes

- [gemini-003/反驳][2026-06-14] 自建 Keycloak 列为“最可能后悔决策”之一：JVM 重、配置繁；家庭 6 人可用 Logto/Authelia/应用层 JWT+白名单 10 分钟搞定，为“企业级练习”拖慢核心 AI 开发。Claude：与本 ADR Trade-off“接受最高资源占用换企业特性全集 + 学习价值”是已知取舍；建议作为过度工程线（与 ADR-006）一并由 human 裁决是否降级。human-001 裁决：不降级，保留 Keycloak——前期为单用户调试，相关 infra 在调试稳定前已购入并部署完毕，不构成阻塞项
