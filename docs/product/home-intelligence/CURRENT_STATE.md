# Current State and Next Coding Session

Evidence is based on the local repository at base commit `c595649`, inspected on 2026-10-07. This is a source review, not a new live-service or physical-device certification.

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

HI-F003 — Canonical Home Domain Model. R1 is active; other R1 features are planned until their own refinement/execution begins.

## Dependency-ready Candidates

HI-S001, HI-S011 and HI-S019 have no Story prerequisites and remain draft until scope approval and a correctly owned Harness REQ exist. HI-S008 is admitted to REQ-013; read its current owner/status from Harness. Its expanded specification includes Floor, room types/labels and editable group-target inventory; the offline inventory package is delivered in PR #26.

## Blocked and Pending Stories

Read admitted engineering blockers from Harness; no unadmitted candidate is marked blocked. The remaining stories await explicit Story prerequisites listed in index.json. Future live HA/device validation requires private endpoint/credentials and a controlled existing device. Deployment of device actions also requires real governed dispatch, durable audit/confirmation and task processing; link the relevant REQ-003/004 gaps when admitting those stories rather than claiming blanket readiness.

## Decisions Required

No unresolved decision prevents the first domain/configuration contract stories. Before action execution, reconcile gateway registry extension, durable confirmation/audit ownership and real executor integration with existing REQ-003/004. Before publishing API contracts, freeze route compatibility against the existing API/BFF draft. Before dispatch integration, reconcile ADR-006 frontmatter through its established review process; do not silently select another broker.

## Domain Contract Delivery

HI-S008 — Define canonical Home, Floor, Area and Device contracts. [REQ-013](../../../harness/tasks/archive/done/features/REQ-013.md) records the accepted typed shared contracts, offline inventory validation and pure target resolution delivered in PR #26. This delivery requires no HA credentials or hardware and supplies canonical identity prerequisites for later mapper/state/mock work.

HI-S009 — Define ProviderBinding contract is delivered through archived [REQ-014](../../../harness/tasks/archive/done/features/REQ-014.md). PR #29 is merged with the P1 instance-alias correction; human-001 accepted the combined delivery and requested done archival. TC-014-01–06 are passing; post-merge runtime checks report 714 passed with zero skips/failures. Provider mappings remain separate from inventory and offline replacement preserves canonical identity.

HI-S010 — Define canonical State contract is admitted to [REQ-015](../../../harness/tasks/features/REQ-015.md). PR #30 is merged, and human-001 explicitly authorized implementation. The shared package now delivers strict offline State validation, per-member ordering updates and derived convergence with TC-015-01–06 implemented for combined review. Desired intent, reported observations, availability, observed_at and epoch/sequence ordering remain separate; unknown/offline cannot become false/zero and ACK alone cannot establish physical convergence. Runtime revision self-checks on Linux aarch64 / CPython 3.12.12 and 3.14.3 each pass 957 cases with zero skips/failures; independent TC/code/feature acceptance remains pending. Owner/status derive from Harness.

## Delivery Order

Contracts HI-S008/009/010/011/019 → schemas HI-S012 → provider/mock HI-S025/026/027. Independently: config HI-S001 → REST/socket HI-S002/003 → events HI-S005. Mapping HI-S013/014/015 and state HI-S016/017/018 then converge at reconnect HI-S007. Invalid-action validation HI-S024 precedes guard HI-S022 and durable audit HI-S023; only then enable HA execution HI-S021 and action API HI-S029. Query API HI-S028 can ship first. HI-S030 closes the full read/action demo. Use the dependency graph, not numbering, as execution order.
