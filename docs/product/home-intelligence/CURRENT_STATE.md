# Current State and Next Coding Session

The original runtime inventory below was inspected at `c595649` on 2026-10-07. Domain contract delivery and admission records are updated through merged main `0443b84` on 2026-10-09. Offline checks do not certify live services or physical devices.

## Already Implemented

- harness/ contains REQ/TC/BUG/ADR standards, registered roles and handoff rules; tools/ and CI contain governance checks.
- apps/home-intelligence-web/ contains an interactive frontend prototype. Its HANDOVER explicitly identifies fictional fixtures and no real home integration.
- toolsets/mcp/goal-mcp/ contains the 36-tool Goal manifest; toolsets/mcp/gateway/gateway/app.py applies JWT, role, tenant and confirmation checks.
- compose.dev.yaml defines PostgreSQL, Redis, RabbitMQ, Keycloak, LiteLLM and Langfuse. Provisioning declarations alone do not certify runtime availability.

## Partially Implemented

- REQ-003 is req_impl_review. Its existing implementation evidence must not be mistaken for a complete Home Intelligence backend.
- The gateway defaults to no executor and fails with 503. Confirmation and audit use bounded process-local storage; durable multi-instance behavior remains work.
- agents/goal/app/graph/__init__.py builds a graph with passthrough nodes and an injected checkpointer. It is not a complete household workflow runtime.
- libs/ has reserved contract/auth packages, while shared production implementations must be inspected before reuse. apps/chatui/ has e2e specifications rather than a delivered application.
- ADR-006 records a human decision to retain RabbitMQ, but frontmatter is still proposed. ADR-016 is accepted and relies on the task/device-bus distinction.

## Not Implemented in the Inspected Runtime

No HA REST/WebSocket home adapter, HA registry mapper, scoped Home State Store, Home capability executor, Mock Home or Home API was found in the inspected apps/agents/libs/toolsets runtime files. Architectural descriptions and frontend fixture objects are not these implementations.

## Active Feature

R1 is active. HI-F003 contracts HI-S008/009/010 are accepted through archived REQ-013/014/015. HI-F004 has accepted HI-S011 Capability base and HI-S012 initial-catalogue deliveries; its Feature remains planned until product refinement/execution is explicitly advanced. Child contract acceptance alone does not complete a Feature.

## Dependency-ready Candidates

HI-S019 is admitted through [REQ-018](../../../harness/tasks/features/REQ-018.md) for specification review; runtime delivery remains pending. HI-S001 and HI-S025 await their own scope approval and Harness admission; HI-S025 also requires delivery of the action contracts. HI-S011 is delivered through archived [REQ-016](../../../harness/tasks/archive/done/features/REQ-016.md). HI-S012 is delivered through archived [REQ-017](../../../harness/tasks/archive/done/features/REQ-017.md). Its schema prerequisite is satisfied for later stories; their remaining dependencies and explicit Harness admission still apply. Read engineering state from Harness.

## Blocked and Pending Stories

Read admitted engineering blockers from Harness; no unadmitted candidate is marked blocked. The remaining stories await explicit Story prerequisites listed in index.json. Future live HA/device validation requires private endpoint/credentials and a controlled existing device. Deployment of device actions also requires real governed dispatch, durable audit/confirmation and task processing; link the relevant REQ-003/004 gaps when admitting those stories rather than claiming blanket readiness.

## Decisions Required

No unresolved decision prevents the first domain/configuration contract stories. Before action execution, reconcile gateway registry extension, durable confirmation/audit ownership and real executor integration with existing REQ-003/004. Before publishing API contracts, freeze route compatibility against the existing API/BFF draft. Before dispatch integration, reconcile ADR-006 frontmatter through its established review process; do not silently select another broker.

## Domain Contract Delivery

HI-S008 — Define canonical Home, Floor, Area and Device contracts. [REQ-013](../../../harness/tasks/archive/done/features/REQ-013.md) records the accepted typed shared contracts, offline inventory validation and pure target resolution delivered in PR #26. This delivery requires no HA credentials or hardware and supplies canonical identity prerequisites for later mapper/state/mock work.

HI-S009 — Define ProviderBinding contract is delivered through archived [REQ-014](../../../harness/tasks/archive/done/features/REQ-014.md). PR #29 is merged with the P1 instance-alias correction; human-001 accepted the combined delivery and requested done archival. TC-014-01–06 are passing; post-merge runtime checks report 714 passed with zero skips/failures. Provider mappings remain separate from inventory and offline replacement preserves canonical identity.

HI-S010 — Define canonical State contract is delivered through archived [REQ-015](../../../harness/tasks/archive/done/features/REQ-015.md). [PR #31](https://github.com/rushwing/ai-family/pull/31) merged as `58f411e`; human-001 accepted AC1–AC7 and TC-015-01–06 under the explicit merge disposition. Post-merge Linux aarch64 / CPython 3.12.12 verification passes 957 tests with zero skips/failures. Desired intent, reported observations, availability and ordering remain separate; unknown/offline never becomes false/zero and ACK cannot establish physical convergence. [Closeout evidence](../../../harness/tasks/evidence/REQ-015-review-acceptance.md) preserves acceptance provenance and environment limits.

HI-S011 — Define versioned Capability base contract is delivered through archived [REQ-016](../../../harness/tasks/archive/done/features/REQ-016.md). [PR #32](https://github.com/rushwing/ai-family/pull/32) merged as `262871e`; human-001 accepted AC1–AC7 and TC-016-01–06 under the final merge disposition. Post-merge Linux aarch64 / CPython 3.12.12 verification passes 1296 tests with zero skips/failures. Strict offline descriptor/catalogue/schema/payload validation supplies descriptive risk/timeout/idempotency/completion metadata; ACK cannot create observed convergence. No provider dispatch, task/deadline/event-correlation engine or six concrete schemas are delivered. [Closeout evidence](../../../harness/tasks/evidence/REQ-016-review-acceptance.md) preserves provenance and environment limits.

HI-S012 — Define six initial capability schemas is delivered through archived [REQ-017](../../../harness/tasks/archive/done/features/REQ-017.md). [PR #34](https://github.com/rushwing/ai-family/pull/34) merged as `0443b84`; human-001 accepted AC1–AC7 and TC-017-01–06 under the final merge/archive disposition. The packaged six-descriptor catalogue and fresh validated accessor reuse REQ-016, with explicit units/ranges, read-only sensor boundaries and two absolute-target actions. Post-merge Linux aarch64 / CPython 3.12.12 verification passes 1493 tests, zero skips/failures. Runtime validates structure and identity/revision; specification content equality is checked by independently transcribed TCs and VCS/release review. Future adapters must validate Capability values before State updates. No provider execution or State integration is delivered. [Closeout evidence](../../../harness/tasks/evidence/REQ-017-review-acceptance.md) preserves merge and acceptance provenance.

## Delivery Order

Delivered contracts HI-S008/009/010/011 and schemas HI-S012 → action contracts HI-S019 (REQ-018 specification review) → provider/mock HI-S025/026/027. Independently: config HI-S001 → REST/socket HI-S002/003 → events HI-S005. Mapping HI-S013/014/015 and state HI-S016/017/018 then converge at reconnect HI-S007. Invalid-action validation HI-S024 precedes guard HI-S022 and durable audit HI-S023; only then enable HA execution HI-S021 and action API HI-S029. Query API HI-S028 can ship first. HI-S030 closes the full read/action demo. Use the dependency graph, not numbering, as execution order.
