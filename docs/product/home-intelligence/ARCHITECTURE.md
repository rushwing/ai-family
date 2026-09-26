# 知微架构边界

## 定位

知微是 `ai-family` 面向家庭设备的 Web 控制面，不建立第二套 Agent 平台。它复用现有身份链、IntentRouter、Planner、MCP Gateway、RabbitMQ、PostgreSQL、Neo4j、LangGraph checkpointer 和 Langfuse。

当前 PR 只迁入前端原型和设计契约，不新增 `HomeAgent`。是否需要独立领域 Agent，应在真实场景跨越现有 Router/Planner 能力边界后再写 ADR。

## 目标链路

```text
Home Intelligence Web
        │
        ▼
Home Intelligence API / BFF
        ├── 状态快照与事件订阅
        ├── 设备/空间/场景读取
        └── 创建、查询、取消任务
        │
        ├──────────────► IntentRouter ─► Planner / Domain Agent
        │                                  │
        ▼                                  ▼
Task Service ─► RabbitMQ ──────────────► MCP Gateway
        │                                  │
        ▼                                  ▼
PostgreSQL / Audit                  Home & Service MCP
                                           │
                                           ▼
                                   Home Device Fabric
                             ┌─────────────┼─────────────┐
                             ▼             ▼             ▼
                     Home Assistant   MQTT / Matter   Native Adapter
                             └─────────────┼─────────────┘
                                           ▼
                                  家庭设备 / NAS / 第三方服务
```

## Monorepo 模块

| 模块 | 位置 | 责任 |
|---|---|---|
| Web | `apps/home-intelligence-web/` | 响应式设备总览、拓扑、场景编排和任务状态 |
| API/BFF | 预留 `apps/home-intelligence-api/` | 面向 Web 聚合鉴权后的读模型和任务命令 |
| MCP | 预留 `toolsets/mcp/home-mcp/` | 向 Agent 暴露设备资源和受治理的类型化动作，不直连终端协议 |
| Device Fabric | 预留 `toolsets/iot/home-device-fabric/` | Home Assistant、MQTT/Matter、Zigbee 和原生 API 的适配与状态归一化 |
| 契约 | 预留 `libs/mcp-contracts/`、`libs/state-schema/` | WoT Device Profile、Task、Event、Scene Schema 和协议映射 |
| Ontology | 预留 `data/ontology/home/` | 空间、设备、能力、成员、网络节点和任务关系 |
| 部署 | 预留 `infra/home-intelligence/` | NAS/树莓派部署、健康检查、备份和回滚 |

预留目录不在本 PR 中创建空实现。正式落地必须由对应 REQ 和 ADR 驱动。

## 家庭设备接入层

采用分层的 Home Device Fabric，不把 Home Assistant、MQTT 或 MCP 当作同一种协议：

- Home Assistant 作为优先的设备集成中枢，复用其 Device/Entity/Area、状态机、Action 和社区集成；
- Matter/Thread、Zigbee2MQTT、厂商本地/云 API 和 NAS/路由器原生 API 位于南向适配层；
- MQTT 5 只承载设备侧状态、事件、availability 和桥接命令；RabbitMQ 继续承担平台任务队列，不被 MQTT 替换；
- W3C WoT Thing Description 的 Property/Action/Event 作为规范化能力契约，并按需引用 SAREF、Brick 与 `zhiwei:` 扩展语义；
- `home-mcp` 是 Agent 的北向入口。终端设备不需要实现 MCP，Agent 也不得直接调用任意 Home Assistant Action 或厂商 API。

知微保存稳定 `device_id`、空间归属、能力、策略和底层实体映射；设备确认状态仍来自接入适配器。自然语言描述用于 Agent 理解，但执行必须依赖版本化的能力 ID、JSON Schema、风险等级和完成条件。详细取舍见 [ADR-016](../../adr/ADR-016-home-device-fabric.md)。

## API 边界

前端只访问中枢 API，不保存厂商凭证：

- `GET /api/twin/snapshot`：家庭孪生快照；
- `GET /api/devices/{device_id}`：设备、状态和能力；
- `POST /api/tasks`：创建异步任务；
- `GET /api/tasks/{task_id}`：查询任务；
- `POST /api/tasks/{task_id}/cancel`：安全取消；
- `GET /api/events`：SSE 或等价事件流；
- `GET /api/ontology`：授权后的家庭关系视图。

接口名称是产品边界草案，不是已冻结契约。冻结前必须形成 Schema 和 ADR。

## 任务模型

普通队列用于下载、统计、通知和批处理。优先队列用于窗帘、卷帘、扫地等需要过程反馈的操作。

RabbitMQ 是平台任务分发与重试的权威队列；MQTT 若被适配器使用，只存在于设备接入边界。两者通过 `task_id`、`idempotency_key` 和 `trace_id` 关联，不共享“已入队即已完成”的错误语义。

优先队列约束：

- 只允许异步任务；
- 消费者必须上报 `accepted`、`running` 和终态；
- 每个任务必须有幂等键、超时、重试策略、风险等级和 `trace_id`；
- 队列优先级不能绕过身份、策略和二次确认；
- 必须限制配额，避免普通队列永久饥饿。

统一状态：

```text
queued → accepted → running → succeeded | failed | cancelled | timed_out
                         └── waiting_confirmation
                         └── waiting_device
```

## 状态一致性

- 前端区分目标状态与设备确认状态；
- 数字孪生显式区分 `desired_state`、`reported_state`、`availability` 和状态新鲜度；
- “任务已发送”不能显示成“设备已完成”；
- 窗帘运动过程中隐藏不可信百分比，停止后读取真实状态；
- 状态事件必须带 `observed_at`、版本或游标，不能让旧事件覆盖新状态；
- 离线设备保持可读，但禁用写操作并显示最后在线时间。

## 安全边界

- 身份链保持 Cloudflare Access/IdP → ChatUI/Web → JWT → Agent → MCP → 数据层；
- 工具自行鉴权，Agent 看见工具不等于成员拥有权限；
- 路由器重启、关键插座断电等动作使用 prepare/confirm/execute；
- 浏览器不接触厂商凭证；
- 任务、工具和设备事件共享 `trace_id`；
- kid 角色继续强制经过 Compliance 和工具侧策略。
