# Current State and Next Coding Session

The original runtime inventory below was inspected at `c595649` on 2026-10-07. Domain/provider/demo/conformance/configuration/REST/WebSocket lifecycle delivery records are updated through merged main `2d986a7` and REQ-024 human final acceptance on 2026-10-15. Offline checks do not certify live services or physical devices.

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

The original `c595649` inspection found no HA REST/WebSocket home adapter, HA registry mapper, scoped Home State Store, production Home capability executor, three-device Mock Home CLI or Home API. Subsequent PR #40 delivers the packaged three-device offline CLI; PR #49 subsequently delivers bounded authenticated read-only REST runtime metadata; PR #51 delivers bounded authenticated WebSocket lifecycle. Subscriptions, registry mapping, state store, capability execution and Home API remain integration gaps. Architectural descriptions and frontend fixture objects are not these implementations.

## Active Feature

R1 is active. HI-F003 contracts HI-S008/009/010 are accepted through archived REQ-013/014/015. HI-F004 has accepted HI-S011 Capability base and HI-S012 initial-catalogue deliveries; its Feature remains planned until product refinement/execution is explicitly advanced. Child contract acceptance alone does not complete a Feature.

## Dependency-ready Candidates

HI-S019 is delivered through archived [REQ-018](../../../harness/tasks/archive/done/features/REQ-018.md) under human final acceptance. HI-S025 is delivered through archived [REQ-019](../../../harness/tasks/archive/done/features/REQ-019.md), with human-accepted typed provider records, protocol and deterministic offline mock. HI-S026 is delivered through archived [REQ-020](../../../harness/tasks/archive/done/features/REQ-020.md), with human-accepted packaged mock switch/curtain/temperature models and offline CLI. HI-S027 conformance is delivered through archived [REQ-021](../../../harness/tasks/archive/done/features/REQ-021.md), with a packaged 51-check offline runner and independent driver/defect probes. Human final acceptance and PR #43 merge are recorded in Harness; read current owner/status there. HI-S001 is delivered through archived [REQ-022](../../../harness/tasks/archive/done/features/REQ-022.md), with human-accepted immutable offline configuration, strict endpoints/limits, redacted diagnostics and finite reconnect inspection merged in PR #46. Read acceptance and evidence from Harness; HI-S002 bounded REST is delivered through archived REQ-023; HI-S003 WebSocket lifecycle is delivered through archived REQ-024. HI-S004 combined health and HI-S005 subscriptions have their transport prerequisite; other prerequisites and explicit admission still apply. HI-S011/012 are delivered through archived REQ-016/017; remaining dependencies and explicit Harness admission still apply to later stories. Read engineering state from Harness.

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

HI-S019 — Define Action Request, Result and Task contracts is delivered through archived [REQ-018](../../../harness/tasks/archive/done/features/REQ-018.md). [PR #37](https://github.com/rushwing/ai-family/pull/37) merged as `b322d45`; human-001 accepted AC1–AC8 and TC-018-01–06 under the final merge disposition and authorized archival. Post-merge Linux aarch64 / CPython 3.12.12 verification passes 1795 tests, zero failures/skips with all six required-runtime flags. Pure helpers enforce strict envelopes, trusted context shape/correlation, scoped type-exact replay/conflict, transitions and validated completion evidence. No provider execution, authentication or durable task/deduplication service is delivered. [Closeout evidence](../../../harness/tasks/evidence/REQ-018-review-acceptance.md) preserves provenance.

HI-S025 — Define provider interface and mock provider is delivered through archived [REQ-019](../../../harness/tasks/archive/done/features/REQ-019.md). PR #39 merged as `58f3883`; human final disposition accepts AC1–AC8 and six passing TCs. Post-merge offline verification passes 114 provider and 1795 shared-contract cases with zero failures/skips. The internal discovery → action → scripted report → completion integration is available; the three-device CLI is subsequently delivered through REQ-020. [Closeout evidence](../../../harness/tasks/evidence/REQ-019-review-acceptance.md) records provenance. HTTP, durable services and physical-device execution remain future work.

HI-S026 — Add mock switch, curtain and temperature sensor is delivered through archived [REQ-020](../../../harness/tasks/archive/done/features/REQ-020.md). [PR #40](https://github.com/rushwing/ai-family/pull/40) merged as `6262456`; human final acceptance covers AC1–AC8 and TC-020-01–06. The packaged [offline CLI](../../../toolsets/iot/home-device-fabric/README.md) emits deterministic discovery, State/timeline and Task/result/rejection evidence. Post-merge Linux aarch64 / CPython 3.12.12 checks pass 177 required fabric/demo and 1795 shared-contract cases, zero failures/skips. [Closeout evidence](../../../harness/tasks/evidence/REQ-020-review-acceptance.md) preserves provenance. HI-S027 broader conformance is specified in [REQ-021](../../../harness/tasks/archive/done/features/REQ-021.md); live adapters, durable services and Feature/Stage completion remain separate.

HI-S027 —Verify provider contracts with mock devices is delivered through archived [REQ-021](../../../harness/tasks/archive/done/features/REQ-021.md). [PR #43](https://github.com/rushwing/ai-family/pull/43) merged as 3ea869a under human final acceptance of AC1–AC8 and TC-021-01–06. The packaged runner/library CLI verifies the fixed 51-case offline profile through supplied provider/driver factories; source evidence records 259 fabric and 1,795 shared cases per tested interpreter, plus direct/sdist installed artifact checks. Post-merge isolated verification passes all 51 report cases. [Closeout evidence](../../../harness/tasks/evidence/REQ-021-review-acceptance.md) preserves provenance. Feature/Stage acceptance and live-adapter certification remain separate.

## Home Assistant Configuration Delivery

HI-S001 is delivered through archived [REQ-022](../../../harness/tasks/archive/done/features/REQ-022.md). [PR #46](https://github.com/rushwing/ai-family/pull/46) merged as `b1c4b35` under human final acceptance of AC1–AC8 and TC-022-01–06. The packaged configuration validates explicit settings and a separate credential, preserves frozen endpoint spelling, redacts ordinary diagnostics, refuses raw serialization and returns a pure finite reconnect tuple. Historical source/artifact evidence records 462 fabric / 1,795 shared cases per tested interpreter; final CI passed all applicable jobs. Post-merge -I/-O smoke verifies configuration rejection/redaction/serialization and schedule behavior. [Closeout evidence](../../../harness/tasks/evidence/REQ-022-review-acceptance.md) records actual provenance. HI-S002 bounded REST is delivered through archived [REQ-023](../../../harness/tasks/archive/done/features/REQ-023.md); HI-S003 lifecycle is delivered through archived REQ-024 under human final acceptance and PR #51 merge. Configuration delivery does not implement HA connectivity or complete HI-F001/R1.

## Home Assistant REST Delivery

[HI-S002](requirements/stories/HI-S002.md) is delivered through archived [REQ-023](../../../harness/tasks/archive/done/features/REQ-023.md). Human-001 accepted AC1–AC8 and TC-023-01–06 and authorized PR #49 merge as `bbe348f` on 2026-10-14. The packaged async client sends one authenticated GET /api/config per admitted call, projects immutable version metadata and uses finite redacted errors, bounded streaming/deadlines and guarded cleanup. Historical final-source evidence records 630 fabric and 1795 shared passes on each of Python 3.12/3.13/3.14, plus twelve installed REST smokes; post-merge -I/-O smoke passes separately. [Closeout evidence](../../../harness/tasks/evidence/REQ-023-review-acceptance.md) records actual attribution and provenance. Verification uses fake servers and requires no HA account, private token or physical device. Live HA certification, subscriptions and HI-F001/R1 completion remain separate; WebSocket lifecycle is delivered through REQ-024. Read engineering scope/status from Harness.

## Delivery Order

Delivered contracts HI-S008/009/010/011 and schemas HI-S012 → delivered action contracts HI-S019 → delivered provider/mock HI-S025 → delivered mock devices/offline CLI HI-S026 → delivered conformance HI-S027 (archived REQ-021). Independently: delivered offline config HI-S001 (archived REQ-022) → delivered bounded REST HI-S002 (archived REQ-023) / delivered WebSocket lifecycle HI-S003 (archived REQ-024) → events HI-S005. Mapping HI-S013/014/015 and state HI-S016/017/018 then converge at reconnect HI-S007. Invalid-action validation HI-S024 precedes guard HI-S022 and durable audit HI-S023; only then enable HA execution HI-S021 and action API HI-S029. Query API HI-S028 can ship first. HI-S030 closes the full read/action demo. Use the dependency graph, not numbering, as execution order.


## Home Assistant WebSocket Lifecycle Delivery

[HI-S003](requirements/stories/HI-S003.md) is delivered through archived
[REQ-024](../../../harness/tasks/archive/done/features/REQ-024.md).
Human-001 accepted AC1–AC8 and TC-024-01–06 after the converged third-pass review
and authorized [PR #51](https://github.com/rushwing/ai-family/pull/51) merge as
`2d986a7` on 2026-10-15. The packaged lifecycle authenticates in order, exposes
finite redacted health, bounds lifetime reconnect attempts and drains shutdown.
[Closeout evidence](../../../harness/tasks/evidence/REQ-024-review-acceptance.md)
records source CI (697 required fabric passes), targeted checks, post-merge
isolated smoke and actual review attribution. Full Windows required suites have
four pre-existing portability failures tracked in
[BUG-033](../../../harness/tasks/bugs/BUG-033.md). No live HA certification,
subscriptions, combined health or Feature/Stage completion is claimed.
