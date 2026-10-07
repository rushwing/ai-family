# Home Intelligence Capability Roadmap

R stages describe capability outcomes. They are separate from platform M milestones, historical P releases and P0–P3 priorities. No distant calendar commitments are implied.

## NOW

### R1 — Home Integration Foundation

**Status:** `active`

**Goal / Outcome:** Connect HA, normalize current state and safely execute vendor-neutral device actions.

**Major capabilities:** HA REST/WebSocket; canonical models/capabilities; mapper; state; guard/audit; mocks; API.

**Exit criteria:** Demonstrate an authorized confirmed action on one existing physical device through the canonical API with reported completion, audit and failure recovery. Mock CI passes without HA.

**Dependencies:** Existing identity/audit/task boundaries; HI-F001–HI-F010.

## NEXT

### R2 — Household Workflow MVP

**Status:** `planned`

**Goal / Outcome:** Deliver reviewed household workflows rather than isolated device commands.

**Major capabilities:** Runtime/persistence; trigger/condition/wait/timeout/retry; confirmation; sleep, aquarium, laundry and mock cleaning; notifications.

**Exit criteria:** Restart a run without duplicated physical effects; demonstrate all four scenarios with defined failure paths and duplicate-feeding prevention.

**Dependencies:** R1; HI-F101–HI-F110.

### R3 — Family Context Engine

**Status:** `planned`

**Goal / Outcome:** Interpret who is present, where, when and what is happening.

**Major capabilities:** Person/presence; occupancy; home/away/sleeping modes; activity; temporal context.

**Exit criteria:** Explain provenance and freshness of scoped context; unknown presence does not become a safety-sensitive assumption.

**Dependencies:** R1 state; R2 runtime; privacy and member authorization.

## LATER

### R4 — Event Intelligence

**Status:** `planned`

**Goal / Outcome:** Derive meaningful household events from correlated device observations.

**Major capabilities:** Temporal windows; correlation; derived events; deduplication; event history.

**Exit criteria:** A repeatable fixture combines observations into an explainable household event without duplicate triggers.

**Dependencies:** R2 triggers; R3 context.

### R5 — Household Memory

**Status:** `planned`

**Goal / Outcome:** Answer authorized questions about household facts, preferences, routines and history.

**Major capabilities:** Separate facts/preferences/routines/events/device and workflow history; structured storage before vectors.

**Exit criteria:** Answer feeding-history and infrastructure-history questions with source evidence; enforce access, retention and deletion policy.

**Dependencies:** R3 context; R4 events; existing privacy/data architecture.

### R6 — Policy & Autonomous Action

**Status:** `planned`

**Goal / Outcome:** Expand autonomous action only within explicit governed boundaries.

**Major capabilities:** Risk tiers; permission; confirmation; audit; compensation/rollback where physically possible.

**Exit criteria:** Low-risk autonomy obeys policy; high-risk actions require human confirmation; irreversible/uncertain outcomes are explicit.

**Dependencies:** R1 guard from day one; R2 workflow; R3 context; R5 memory.

### R7 — AI Planner / Household Agent

**Status:** `planned`

**Goal / Outcome:** Turn ambiguous household intent into a reviewed structured executable plan.

**Major capabilities:** Intent interpretation; multistep plans; context reasoning; recommendations; exception suggestions.

**Exit criteria:** A structured plan passes policy validation before execution; no LLM call can dispatch to a device provider directly.

**Dependencies:** R2 workflow; R3 context; R5 memory; R6 policy; platform planner work.

### R8 — Spatial Intelligence

**Status:** `planned`

**Goal / Outcome:** Model floors, rooms, areas, zones and static/movable locations without a vendor dependency.

**Major capabilities:** Canonical maps; robot rooms; optional BLE/UWB/camera/Matter occupancy integrations.

**Exit criteria:** Replace a robot/map adapter without changing canonical spatial IDs or workflow references.

**Dependencies:** R1 canonical identities; R3 context.

### R9 — Multimodal Home Understanding

**Status:** `planned`

**Goal / Outcome:** Interpret visual household observations within a local-first privacy boundary.

**Major capabilities:** Camera/RTSP/ONVIF; image events; VLM; door/package/pet/floor observations.

**Exit criteria:** Consent, local processing, scoped access and retention are verified; uncertain recognition cannot directly trigger unsafe action.

**Dependencies:** R4 events; R6 policy; R8 spatial model.

### R10 — Natural Interaction

**Status:** `planned`

**Goal / Outcome:** Expose one governed backend through multiple household interaction channels.

**Major capabilities:** Web/mobile; Telegram; voice; Siri/Shortcuts; notifications.

**Exit criteria:** Equivalent authorized intent from two channels produces the same reviewed action semantics; channels cannot bypass policy.

**Dependencies:** R1 API; R2 notifications; R7 plans. Existing web prototype is a starting asset.

### R11 — Reliability & Home Operations

**Status:** `planned`

**Goal / Outcome:** Operate the household service with recoverable failures on NAS/Pi/home servers.

**Major capabilities:** Health/watchdog; metrics/traces/alerts; dead letters; validation; backup; disaster recovery.

**Exit criteria:** An outage and restore drill meets documented recovery targets and produces runtime evidence; local manual control remains available.

**Dependencies:** Each stage must already satisfy baseline reliability; platform REQ-010 and operational ADRs.

### R12 — Open Home Intelligence Platform

**Status:** `planned`

**Goal / Outcome:** Extend adapters, capabilities and workflows without changing the core.

**Major capabilities:** Plugin/Adapter/Capability/Workflow SDKs; APIs/webhooks; MCP integration; developer documentation.

**Exit criteria:** A reference third-party adapter passes contracts and policy registration without core modifications.

**Dependencies:** R1 contracts; R2 workflow; R6 policy; R11 operations.

## Refinement Boundary

R1 has detailed features and candidate stories. R2 has detailed features only. R3–R12 remain roadmap entries. Existing historical future stories are preserved as deferred references, not expanded or activated. Baseline security and reliability apply in R1; R6/R11 deepen them rather than introduce them for the first time.
