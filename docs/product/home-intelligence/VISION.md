# Home Intelligence Vision

## Purpose

Build ai-family into a household intelligence platform that understands current home state, member context and household history, then recommends or performs actions within explicit authorization and safety boundaries. The product name is Zhiwei · Home Intelligence. Its guiding phrase is “From small signals, understand the whole; let every event leave a voice.”

## Product Principles

- Move from explicit device commands to explainable household workflows and context-aware decisions.
- Preserve member agency: users can inspect, approve, stop and understand consequential actions.
- Develop against mocks before requiring new hardware; adapters carry vendor variability.
- Define features by demonstrable outcomes and stories by independently mergeable increments.
- Detail only the active stage; avoid speculative dates, estimates and persistent implementation tasks.

## Architecture Principles

- Reuse the ai-family platform, modular monorepo, shared contracts and existing Harness.
- Home Assistant supplies broad integration; native adapters cover unsupported services. Do not rebuild vendor protocol stacks.
- Home/Area/Device/Capability/State/ProviderBinding use stable canonical identities. Provider identifiers do not propagate into Agent or Workflow logic.
- WoT interaction contracts, MCP governance, RabbitMQ task semantics and PostgreSQL durability retain existing ADR authority.
- Structured facts use structured storage; memory is not synonymous with a vector database.

## Safety Principles

- Every physical action passes trusted identity, policy, schema validation and auditable execution.
- Write confirmation follows ADR-010 from R1; agents cannot approve their own actions.
- Desired state and accepted transport requests never stand in for confirmed physical state.
- Unknown outcomes, stale state and missing permissions fail closed for unsafe writes.
- Privacy is local-first; inventory, images, secrets and member context have explicit access and retention boundaries.
- Preserve existing child restrictions; later autonomy never silently loosens them.

## Product Boundary

Home Intelligence adds household modeling, context, capabilities, workflows, event understanding, memory and governed reasoning above HA/Matter/MQTT/vendor integrations. It does not replace those protocol ecosystems or reduce its scope to a device dashboard. GoalAgent and other platform domains remain part of ai-family; the R roadmap describes the household product direction.

## Planning Authority

Read [requirements operating rules](requirements/README.md) before selecting a story. This Vision is stable; revise it only when product direction changes, not at every sprint.
