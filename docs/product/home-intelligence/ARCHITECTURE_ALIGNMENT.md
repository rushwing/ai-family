# Architecture Alignment with the Existing Platform

## Authority

This is an English integration specification, not a replacement ADR. [ADR-016](../../adr/ADR-016-home-device-fabric.md) already selects HA as the primary gateway, canonical WoT capabilities and provider bindings. [ADR-010](../../adr/ADR-010-mcp-tool-architecture.md) already defines safe tool execution and user confirmation. [ADR-006](../../adr/ADR-006-rabbitmq-bus.md) records the human decision to retain RabbitMQ; its proposed frontmatter must be reconciled through existing review rules. No duplicate ADR-001/002/003 files are created.

## Governed Paths

```text
Web / other authenticated channels -> Home API/BFF -> Task Service
                                              -> Guard / policy / confirmation
                                              -> Capability mapping -> Adapter -> HA or Mock
Agent / Planner -> MCP Gateway -> home-mcp -----> same guarded task/action boundary
State: HA / Mock -> normalized events + mapper -> Home State Store -> canonical queries
Durability: task/outbox/audit/confirmation -> PostgreSQL with scoped access
Dispatch: RabbitMQ; device-side transport where required: MQTT
```

All entry points must converge on the shared action policy. Tool-side authorization remains mandatory; passing the gateway is not sufficient proof of permission. A new home API does not depend on an unfinished GoalAgent executor for pure contract/query work, but cannot enable ungoverned physical actions.

## Canonical Model

Home, Area, Device, Capability, State and ProviderBinding form a vendor-neutral contract. HA entity_id, vendor ID, MIoT property, robot room ID, Matter endpoint and MQTT topic remain adapter/binding data. Workflows, Agent plans and primary API payloads use canonical IDs. WoT properties/actions/events organize capability semantics; names such as Switchable and Positionable are typed project vocabulary within that existing model.

## Shared Modules

Use libs/state-schema and libs/mcp-contracts for shared models, libs/auth for reusable authorization, toolsets/iot/home-device-fabric for adapters and toolsets/mcp/home-mcp for governed northbound tools when their Stories are admitted. apps/home-intelligence-api remains the existing reserved API/BFF location. These are logical module boundaries; do not add empty implementations, a new HomeAgent, Kubernetes or independent services merely to satisfy a diagram.

## State and Execution

A rebuildable in-memory cache is acceptable for R1 current state. It must retain desired/reported separation, availability, freshness and ordering; reconcile from a fresh snapshot after restart. Action tasks, idempotency, audit and confirmation require durable state. All device writes remain asynchronous tasks under ADR-016. ACK means accepted, not physical completion. Capability completion_policy controls whether acknowledgement, an event or converged state determines success.

## Safety from R1

Trusted identity and member/device scope, allowed capabilities, parameter validation, risk checks and explicit user confirmation precede writes. Unsupported actions fail closed. Reuse the existing HMAC/session-bound confirmation architecture; agents cannot issue their own confirmation. Preserve child structured/read-only restrictions. High-risk unsupported actions remain disabled. R6 adds sophisticated policy and autonomy without deferring these baseline controls.

## API Compatibility

The prompt suggests GET /home, /areas, /devices, /devices/{id}, /state and POST /actions. Existing ARCHITECTURE.md proposes /api/twin/snapshot, /api/devices/{device_id}, /api/tasks, task lookup/cancellation and /api/events. Preserve those existing draft boundaries and specify equivalent canonical resources in HI-S028/029. Freeze naming, schemas and compatibility before implementation; do not maintain two aliases accidentally or claim existing routes are deployed.

## Technology Decisions

Retain Python/FastAPI, existing MCP trust boundaries, PostgreSQL/RLS, RabbitMQ tasks, local-first device integration and existing LangGraph orchestration direction. Internal normalization may use direct typed calls within a module; that is not a replacement task bus. MQTT remains device-facing. No new NATS/Kafka choice or premature microservice split is introduced. Reuse existing ADRs for the three requested decisions; only create a new proposed ADR when an actual uncovered tradeoff needs review.
