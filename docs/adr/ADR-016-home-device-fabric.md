---
adr_id: ADR-016
title: "家庭设备接入层：Home Assistant 集成中枢 + WoT 语义契约 + MCP 北向治理"
status: accepted
date: 2026-09-27
deciders: [human-001]
informed_by: []
supersedes: null
linked_reqs: [REQ-011]
---

## Context（背景与约束）

知微需要接入 Matter/Thread、Zigbee、Wi-Fi、本地 API、厂商云和只能被动观测的异构设备，并为未来多住宅、多楼层扩展保留统一模型。直接为每个品牌重复实现发现、状态、动作和离线判断会形成长期维护负担；让 Agent 直接理解厂商协议或 Home Assistant Entity/Action 又会把实现细节、凭证和高风险操作暴露到推理层。

AI Agent 需要的不是原始协议，而是稳定设备身份、空间关系、可信状态、类型化能力、风险和完成条件。自然语言描述有助于推理，但不能替代可校验的执行 Schema。

本决策必须与既有边界一致：

- [ADR-006](ADR-006-rabbitmq-bus.md) 的 RabbitMQ 继续承载平台异步任务、优先级、重试和死信；
- [ADR-010](ADR-010-mcp-tool-architecture.md) 的 MCP Gateway、工具侧鉴权和 Draft-First 继续生效；
- Home Assistant 是集成平台和运行时，不被定义成通用终端协议；
- 当前 PR 只冻结架构选择，不实现接入服务、完整 Ontology 或设备驱动。

## Options（候选项）

### Option A：每个设备或厂商在 MCP 内直接实现协议

**Pros:** 链路短；早期单设备 PoC 快。

**Cons:** 每个 MCP 重复实现发现、重连、availability、状态缓存和协议差异；设备与 Agent 契约耦合；更换品牌会破坏场景；低功耗终端无法合理运行 MCP。

### Option B：Home Assistant 作为唯一模型，向 Agent 暴露原始 Entity 和任意 Action

**Pros:** 最大化复用社区集成；实现最少。

**Cons:** HA Entity ID 和平台语义成为永久业务契约；Agent 需要理解集成细节；任意 Action 难以做能力级授权、风险分级、幂等和完成判定；知微 Ontology 退化为 HA 数据镜像。

### Option C：分层 Home Device Fabric（选定）

**Pros:** 复用 Home Assistant 和开放协议生态，同时用稳定语义隔离厂商实现；MCP 只暴露经过治理的能力；支持不经过 HA 的 NAS、路由器和中枢原生适配器；便于逐设备迁移和测试。

**Cons:** 需要维护实体映射、状态归一化和一条额外适配边界；Home Assistant、MQTT、RabbitMQ 的职责必须清晰，否则会产生双写和双队列。

## Decision（决策）

采用 **Option C：Home Device Fabric**，分为五层。

### 1. 南向协议与驱动

- 新购设备优先 Matter over Thread/Ethernet/Wi-Fi；Matter 未覆盖的厂商高级能力可保留专用集成；
- Zigbee 设备优先通过 Zigbee2MQTT 接入；
- Home Assistant 作为默认集成中枢，复用其 Device、Entity、Area、状态和 Action 生态；
- NAS、树莓派、路由器以及 HA 无稳定支持的设备允许使用独立 Native Adapter；
- 云依赖、逆向协议和只读能力必须在设备元数据中显式标记，不能伪装为可靠本地能力。

### 2. 规范化能力与数字孪生

使用 W3C WoT Thing Description 1.1 的 `properties`、`actions` 和 `events` 作为 Device Profile 的基础交互模型；按需引用 SAREF 的设备/功能/测量语义、Brick 的 Building/Floor/Room/Equipment 关系，并用 `zhiwei:` 命名空间表达家庭成员、任务队列、风险、确认和场景等项目概念。

知微 Device Registry 是稳定 `device_id`、用户命名、空间归属、能力版本、策略和协议映射的权威来源；设备 `reported_state` 与 `availability` 的事实来源仍是对应 Adapter。Home Assistant Entity ID、MQTT Topic、Matter Node/Endpoint 和厂商 ID 只作为可替换映射，不得成为场景或 Agent 计划的永久主键。

能力必须同时提供机器契约和人类语义：稳定 `capability_id`、输入/输出 JSON Schema、风险等级、幂等规则、超时和完成策略是执行依据；自然语言 `title`/`description` 只用于理解与展示。

### 3. 总线边界

- MQTT 5 仅作为设备边界的轻量 publish/subscribe 总线，并服务 Zigbee2MQTT、状态、事件、availability 和必要的桥接命令；
- RabbitMQ 继续作为平台 Task Service 的权威任务队列，负责普通/优先队列、重试、死信和消费者调度；
- MQTT 状态和 availability 可以 retained，命令不得 retained；
- 两层通过 `task_id`、`idempotency_key`、`trace_id` 和设备映射关联；任何传输层 ACK 都不等于物理动作完成。

### 4. MCP 北向接口

`home-mcp` 代表家庭设备领域向 Agent 暴露资源和工具，而不是要求每台终端实现 MCP：

- Resources 提供授权后的设备、空间、能力和状态视图；
- Tools 接收稳定 `device_id`、`capability_id` 和类型化参数；
- 禁止向 Agent 暴露任意 `homeassistant.call_service`、任意 MQTT publish 或厂商原始 API；
- Adapter 负责把规范动作翻译成 HA Action、MQTT、Matter 或 Native API；
- MCP Gateway 和具体工具仍按 ADR-010 执行白名单、JWT、审计、风险分级与确认。

### 5. 状态与任务语义

所有设备写操作在知微边界均表现为异步任务，即使底层 API 是同步调用。统一区分：

- `desired_state`：用户或 Agent 请求达到的状态；
- `reported_state`：设备或 Adapter 最后确认的状态；
- `availability`、`observed_at` 和版本/游标：状态是否仍可信；
- `completion_policy`：`ack_only`、`event_confirmed` 或 `state_converged`；
- `accepted`：接入层接收请求，不代表设备已经完成。

窗帘等过程动作进入优先队列并持续上报 `moving`/终态；运动期间不展示未经设备确认的实时百分比。路由器重启、关键插座断电、NAS 关机等高风险动作继续使用 prepare/confirm/execute。

## Trade-off（明确放弃了什么）

- 放弃“Home Assistant 就是全部后端”的最小实现，换取可替换驱动、稳定 Ontology 和能力级治理；
- 放弃“每台设备直接暴露 MCP”的表面统一，避免把 AI 协议推到资源受限终端和厂商协议层；
- 接受 RabbitMQ 与 MQTT 可能同时存在，但通过任务总线/设备总线的硬边界避免职责重叠；
- 第一阶段不引入完整 RDF Store/OWL 推理器，只采用版本化 JSON-LD/WoT Profile 和受控词表；复杂图推理仍按 ADR-005 的 Neo4j 路径演进。

## Consequences（影响）

- 预留 `toolsets/iot/home-device-fabric/` 承载 Adapter runtime，`toolsets/mcp/home-mcp/` 只承载北向 MCP；
- `libs/mcp-contracts/` 与 `libs/state-schema/` 需要加入 WoT Device Profile、Task/Event 和映射契约；
- `data/ontology/home/` 保存受版本管理的空间、设备、能力词表和外部 Ontology 映射；
- 每个 Adapter 必须通过契约测试，至少覆盖 discovery、identity、availability、状态新鲜度、动作映射、幂等、超时和错误归一化；
- 场景和工作流只引用知微稳定 ID 与 capability ID，不引用 HA Entity、MQTT Topic 或厂商命令；
- 部署可以把 Home Assistant、Matter Server、Mosquitto、Zigbee2MQTT 和 Agent 分成独立容器/节点，故障时仍保留本地手动控制与最小自动化能力。

## Revisit Trigger（重审触发条件）

- Home Assistant 集成层连续造成不可接受的可用性或升级阻塞，需把关键设备迁为 Native Adapter；
- Matter 覆盖家庭关键设备及高级能力后，可减少厂商/HA 适配器，但不改变 WoT/MCP 北向契约；
- MQTT 不再被 Zigbee2MQTT 或任何设备适配器使用，评估移除独立 Broker；
- JSON-LD/关系表无法满足跨住宅、多楼层或复杂设备关系查询，评估将完整 Ontology 实例化到 Neo4j/RDF 工具链；
- W3C WoT、SAREF 或 Brick 出现不兼容大版本时，先版本化迁移映射，不直接破坏现有 Device Profile。

## References

- <https://developers.home-assistant.io/docs/architecture/core/>
- <https://developers.home-assistant.io/docs/architecture/devices-and-services/>
- <https://www.w3.org/TR/wot-thing-description/>
- <https://saref.etsi.org/>
- <https://docs.brickschema.org/brick/overview.html>
- <https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html>
- <https://www.home-assistant.io/integrations/matter/>
- <https://www.zigbee2mqtt.io/guide/usage/mqtt_topics_and_messages.html>

## Review Notes（评审追加区）

（暂无）
