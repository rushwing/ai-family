---
adr_id: ADR-011
title: "文件存储与备份：NAS 双形态（SMB 保留 + MinIO S3 网关）+ VPS 异地备份"
status: proposed
date: 2026-06-11
deciders: [human-001]
informed_by: []
supersedes: null
linked_reqs: [REQ-002]
---

## Context（背景与约束）

绿联 NAS DX4600 现状：家庭多媒体（电影/剧/音乐/照片）与学习资料已按 SMB 共享使用，家人有既有使用习惯。
平台需求：①程序化文件访问（摄取管线读学习资料、StudyAgent 存拍题图片、报表归档）需要带权限模型的 API；
②DataAgent 要检索媒体元数据；③用户明确担心"重要信息本地托管的数据丢失风险"——需要异地备份。

## Options

### Option A: SMB 直挂给所有服务
**Pros:** 零新组件，家人习惯不变
**Cons:** 挂载凭证 = 整库权限，无 per-member 隔离；无对象级审计；容器挂 SMB 的稳定性与权限映射都是坑

### Option B: MinIO 全面接管（家人也走 S3/网页）
**Pros:** 权限模型最统一
**Cons:** 强迫家人改变媒体使用习惯（视频播放器、照片备份都依赖 SMB/专用 App），不现实

### Option C: 双形态——SMB 保留人用面，MinIO 承载机用面（选定）
**Pros:** 家人零感知；平台侧获得 S3 API + bucket policy + 版本控制 + 事件通知（对接 RabbitMQ 触发摄取）；
S3 是企业对象存储通用接口，学习价值与可迁移性（未来换云）最高
**Cons:** 同一份学习资料存在"SMB 目录（人放入）→ MinIO bucket（平台镜像）"的同步问题，需要明确单向流

## Decision

**Option C。** MinIO（单节点模式）部署于 NAS，数据目录落 NAS 存储池。

桶规划与数据流向：

| Bucket | 内容 | 写入方 | 隔离 |
|---|---|---|---|
| `member-{sub}` | 成员私有文件（拍题图、报告、Agent 产物） | 平台（工具侧鉴权后） | bucket-per-member + policy |
| `library-inbox` | 学习资料入口（SMB 目录单向同步进来） | 同步任务 | 家庭共享读 |
| `media-meta` | DataAgent 的媒体索引产物（缩略图/元数据），**不复制媒体本体** | DataAgent | 共享读 |
| `artifacts` | 报表/导出归档 | 平台 | 按前缀 policy |

- 媒体本体（电影/照片原件）**不进 MinIO**：DataAgent 经只读 SMB 挂载扫描生成元数据入 PG/`media-meta`，播放仍走家人现有方式
- 学习资料单向流：SMB `学习资料/` → 定时 rclone 同步 → `library-inbox` → S3 事件 → RabbitMQ → 摄取管线（ADR-004/005）

备份链路（3-2-1 原则的家庭近似）：
- PG：pgBackRest 全量周备 + WAL 归档 → MinIO `backups` 桶 → restic 加密推 VPS（或 B2/R2 对象存储，按价格定）
- MinIO 关键桶（member-*、artifacts）：restic 加密 → VPS；媒体本体不进异地备份（体量大、可重获得，接受丢失风险并明示）
- Neo4j：每日离线 dump → 同链路
- **恢复演练进 REQ-002 验收**：备份没有演练过 = 没有备份

## Trade-off

- 接受"同一资料两份存储 + 单向同步"的冗余，换取家人零迁移成本与平台侧完整权限模型
- 媒体本体不做异地备份——明确接受该数据类别的丢失风险（与用户"重要信息"的界定一致：重要 = DB/私有文件/图谱，媒体可再获取）

## Consequences

- NAS 内存预算需容纳 MinIO（~300MB）；存储池规划单独留 backups 配额
- S3 事件驱动摄取使"放文件进 SMB 目录"成为家人导入学习资料的唯一动作（产品体验目标）

## Revisit Trigger

- 绿联系统升级影响 Docker/SMB 行为（NAS 系统是本方案最不可控因子，故所有平台数据皆可从备份重建）
- VPS 备份成本 > 对象存储（R2/B2）成本（切换备份目的地）

## Review Notes

（待评审追加）
