---
adr_id: ADR-007
title: "内外网穿透：Tailscale mesh + Cloudflare Tunnel/Access（FRP+VPS 落选）"
status: accepted
date: 2026-06-11
deciders: [human-001]
informed_by: [gemini-005, gemini-r2, claude-code-001]
supersedes: null
linked_reqs: [REQ-002]
---

## Context（背景与约束）

节点分布：家庭局域网（Pi5、NAS、MacMini）、云端（小额 VPS 备份机）、移动终端（家人手机/笔记本在外网）。
需求：①节点间互访（管理、DB 访问、备份流量）；②家人在外网用公网域名访问 ChatUI；③**零公网入站端口**；
④家有未成年人使用，入口必须有强认证。用户有公网域名，已拍板本方案。

## Options

### Option A: Tailscale（mesh VPN）+ Cloudflare Tunnel/Access（选定）
**Pros:**
- Tailscale：WireGuard mesh，NAT 穿透免配置，ACL 声明式管理"谁能访问哪个节点哪个端口"；全节点（含手机）一张内网
- CF Tunnel：cloudflared 出站长连接发布 ChatUI，源站零入站端口；自带 WAF/DDoS/TLS
- CF Access：在应用之前的认证层（可对接平台 IdP 的 OIDC），公网扫描者连登录页都看不到
- 两者免费档完全覆盖家庭规模

**Cons:** 控制面依赖两家外部 SaaS（Tailscale 协调服务器、Cloudflare）；CF Tunnel 对非 HTTP 流量支持有限；流量经 CF 有合规上的"第三方可见性"考量（TLS 到 CF 终止）

### Option B: VPS + FRP + 自建反代（Nginx/Caddy）
**Pros:** 全链路自主，端口/证书/防火墙全自己管，学习价值高
**Cons:** 安全责任全在自己（证书轮换、fail2ban、补丁）；VPS 成为单点+攻击面；省下的 SaaS 依赖换成持续运维负担——对"家里有小孩账号"的系统，入口安全不容自建试错

### Option C: 纯 Tailscale（无公网发布）
**Pros:** 攻击面最小
**Cons:** 家人设备必须全装 Tailscale 客户端，分享/临时访问不便；放弃公网域名价值

## Decision

**Tailscale 承载全部节点间流量（管理、DB、备份、MCP 内部调用）；Cloudflare Tunnel + Access 作为唯一公网入口，只发布 ChatUI（及后续 PWA）。**

关键安全设计（ACL 细节以 docs/design/02 §3 为准）：
- Tailscale ACL：`tag:infra`（Mac Mini runtime / NAS / VPS）互通受限端口白名单；`tag:ingress`（Pi5 公网入口）**最小可达面**——dst 限定 `tag:runtime`（仅 Mac Mini，同时持 infra+runtime 两 tag）的 `agent-core/mcp:8000-8099`，**故 ingress 触不到 NAS/VPS 任何端口**；`tag:member`（家人设备）只许达 ChatUI/IdP 端口；小孩设备 tag 不可达管理台
- **ingress 非 Subnet Router**：Pi5 作为公网入口节点不承担 Tailscale Subnet Router 角色（不代理整个家庭网段）；ingress→runtime 仅是端口白名单的单跳，且 dst 收敛到 `tag:runtime` 单一节点。即便 Pi5 被攻破，blast radius 收敛到 runtime 的 `:8000-8099`，无法横向打穿 NAS 数据面或内网其余主机（BUG-008）
- CF Access policy：仅允许家庭成员邮箱列表，会话时长 24h；Access JWT 在 ChatUI 侧二次校验（防 CF 配置失误直通）
- 敏感面板（RabbitMQ 管理台、Langfuse、Neo4j Browser、IdP admin）**只在 Tailscale 内**，永不经 Tunnel 发布
- VPS 防火墙：仅允许 Tailscale UDP 打洞与出站，SSH 仅监听 tailnet 地址

## Trade-off

- 接受 Tailscale/CF 两个 SaaS 控制面依赖（数据面 Tailscale 是端到端 WireGuard，CF 仅见 ChatUI HTTP 流量；高敏数据不经公网入口流动）
- 放弃 FRP 自建的全链路掌控学习——以 Tailscale ACL/CF Access 策略工程作为替代学习面
- 接受 TLS 在 CF 边缘终止（家庭非合规场景可接受；ChatUI 与后端间仍是 tailnet 加密）

## Consequences

- 所有服务监听 tailnet 接口或 localhost，docker-compose 网络不映射宿主公网端口
- 域名 DNS 托管迁至 Cloudflare；Tunnel 配置文件进 infra 配置库（凭证走 secret）
- 家人手机装 Tailscale 仅用于应急管理场景，日常走公网域名

## Revisit Trigger

- Tailscale/CF 免费档政策变化影响使用
- 出现必须发布非 HTTP 服务到公网的需求（届时单独评估，而非放宽本决策）

## Review Notes

- [gemini-005][2026-06-14] 02 部署图显示 CF Tunnel 直连 Pi5(ingress) 但未画 Pi5→Mac Mini/K3s 集群的安全路由；若用 Subnet Router 需明确 ACL，否则 Pi5 被攻破 → 内网全穿透 → 已立 BUG-008（02 SVG 补 Tailscale 网段与 K3s ingress 交互连线，正文补 subnet-router ACL）。human-001 裁决：accept（2026-06-14, BUG-008）
- [gemini-r2][2026-06-14] 再次：02 图示 CF Tunnel 直连 RPi，但未画 RPi→Mac Mini（K3s Ingress/外部 runtime）的路由，正文缺 Subnet Router ACL——强化 BUG-008（混合编排下尤其要明确 Pi5 作 ingress 到 Mac 的 ACL 最小化，防 Pi5 被攻破后内网全穿透）。human-001 裁决：accept（2026-06-14, 强化 BUG-008）
- [claude-code-001][2026-06-14] BUG-008 已修复：02 §1 SVG 补 ① chatui(Pi5)→agent-core(Mac Mini)、② agent-core→PG/Neo4j/MinIO(NAS) 路由连线与图例；§3 ACL 拆出 `tag:ingress` 并加 ingress→runtime 端口收敛规则 + Subnet Router 风险说明；本 ADR Decision 补「ingress 非 Subnet Router、blast radius 收敛」。状态闭环 → BUG-008 resolved。
