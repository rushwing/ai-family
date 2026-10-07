# Source and Legacy Crosswalk

## Source

Source: AI-Family Requirements Design Prompt, authored by Daniel Wong, dated 2026-10-07, supplied as a local Markdown ZIP corresponding to the linked Notion page. The original source is not republished into the public repository; this delivery records its interpreted scope in English. Prompt IDs F001–F010, F101–F110 and S001–S030 are source labels. Primary new IDs are HI-F* and HI-S*. Existing ZW-* and REQ-* identities are unchanged.

## Legacy Scope Policy

The original 68-story workbook and roadmap.yaml remain the historical UI/product baseline with their existing version. New HI stories are narrower backend increments, not renamed copies. The table below supplies coverage/refinement references. Before admitting an overlapping legacy backend Story, use its HI slices or record a residual gap; never schedule both copies of the same increment. Existing future stories and sample tasks are preserved, deferred from new R1 execution and not expanded. Existing In Progress flags often describe prototype interaction, not real backend completion. No such flags are rewritten as done.

## Stage Alignment

| New stage | Existing release/platform relationship |
|---|---|
| R1 | Parts of product P0 contracts and P1 twin/control; platform M1 assets supply identity/data/tool foundations. |
| R2 | Product P2 scenes/runtime; distinct from the platform M2 milestone. |
| R3–R6 | Context/event/memory/policy outcomes overlap portions of historical P3/P4; no one-to-one mapping is claimed. |
| R7 | Product P3 planning; depends on relevant platform Router/Planner work, not calendar equivalence to M2. |
| R8–R10 | Extend spatial, multimodal and interaction direction without expanding current stories. |
| R11 | Deepens operations alongside platform REQ-010/M5; baseline safety/recovery starts in R1. |
| R12 | Extensibility beyond the existing modular monorepo and MCP domain architecture. |

## Feature Coverage

| Source | Primary Feature | Related legacy Epic |
|---|---|---|
| F001 | [HI-F001](requirements/features/HI-F001.md) | ZW-EP-13 |
| F002 | [HI-F002](requirements/features/HI-F002.md) | ZW-EP-03 |
| F003 | [HI-F003](requirements/features/HI-F003.md) | ZW-EP-01, ZW-EP-02 |
| F004 | [HI-F004](requirements/features/HI-F004.md) | ZW-EP-02 |
| F005 | [HI-F005](requirements/features/HI-F005.md) | ZW-EP-01, ZW-EP-13 |
| F006 | [HI-F006](requirements/features/HI-F006.md) | ZW-EP-03 |
| F007 | [HI-F007](requirements/features/HI-F007.md) | ZW-EP-12, ZW-EP-13 |
| F008 | [HI-F008](requirements/features/HI-F008.md) | ZW-EP-15, ZW-EP-16 |
| F009 | [HI-F009](requirements/features/HI-F009.md) | ZW-EP-13 |
| F010 | [HI-F010](requirements/features/HI-F010.md) | ZW-EP-03, ZW-EP-12 |
| F101 | [HI-F101](requirements/features/HI-F101.md) | ZW-EP-08, ZW-EP-11 |
| F102 | [HI-F102](requirements/features/HI-F102.md) | ZW-EP-11 |
| F103 | [HI-F103](requirements/features/HI-F103.md) | ZW-EP-08 |
| F104 | [HI-F104](requirements/features/HI-F104.md) | ZW-EP-08, ZW-EP-15 |
| F105 | [HI-F105](requirements/features/HI-F105.md) | ZW-EP-09 |
| F106 | [HI-F106](requirements/features/HI-F106.md) | ZW-EP-09 |
| F107 | [HI-F107](requirements/features/HI-F107.md) | ZW-EP-09 |
| F108 | [HI-F108](requirements/features/HI-F108.md) | ZW-EP-09, ZW-EP-13 |
| F109 | [HI-F109](requirements/features/HI-F109.md) | ZW-EP-11, ZW-EP-16 |
| F110 | [HI-F110](requirements/features/HI-F110.md) | ZW-EP-12 |

## Story Coverage

| Source | Primary backend slice | Related legacy Story scope |
|---|---|---|
| S001 | [HI-S001](requirements/stories/HI-S001.md) — Define Home Assistant configuration | New explicit HA foundation gap |
| S002 | [HI-S002](requirements/stories/HI-S002.md) — Add authenticated Home Assistant REST client | New explicit HA foundation gap |
| S003 | [HI-S003](requirements/stories/HI-S003.md) — Define Home Assistant WebSocket lifecycle | New explicit HA foundation gap |
| S004 | [HI-S004](requirements/stories/HI-S004.md) — Expose Home Assistant integration health | New explicit HA foundation gap |
| S005 | [HI-S005](requirements/stories/HI-S005.md) — Subscribe to HA state changes | ZW-ST-0302 |
| S006 | [HI-S006](requirements/stories/HI-S006.md) — Normalize HA state change events | ZW-ST-0302 |
| S007 | [HI-S007](requirements/stories/HI-S007.md) — Reconcile current state after reconnect | ZW-ST-0302, ZW-ST-0304 |
| S008 | [HI-S008](requirements/stories/HI-S008.md) — Define canonical Home, Area and Device contracts | ZW-ST-0101, ZW-ST-0201 |
| S009 | [HI-S009](requirements/stories/HI-S009.md) — Define ProviderBinding contract | ZW-ST-1302 |
| S010 | [HI-S010](requirements/stories/HI-S010.md) — Define canonical State contract | ZW-ST-0304 |
| S011 | [HI-S011](requirements/stories/HI-S011.md) — Define versioned Capability base contract | ZW-ST-0201, ZW-ST-0202 |
| S012 | [HI-S012](requirements/stories/HI-S012.md) — Define six initial capability schemas | ZW-ST-0202 |
| S013 | [HI-S013](requirements/stories/HI-S013.md) — Discover HA registries and state | ZW-ST-1303 |
| S014 | [HI-S014](requirements/stories/HI-S014.md) — Map registries into canonical home objects | ZW-ST-0102, ZW-ST-0103, ZW-ST-1302 |
| S015 | [HI-S015](requirements/stories/HI-S015.md) — Infer supported capabilities deterministically | ZW-ST-0202, ZW-ST-1302 |
| S016 | [HI-S016](requirements/stories/HI-S016.md) — Implement scoped current-state store | ZW-ST-0301 |
| S017 | [HI-S017](requirements/stories/HI-S017.md) — Apply normalized events monotonically | ZW-ST-0302, ZW-ST-0304 |
| S018 | [HI-S018](requirements/stories/HI-S018.md) — Expose scoped home-state query service | ZW-ST-0301 |
| S019 | [HI-S019](requirements/stories/HI-S019.md) — Define Action Request, Result and Task contracts | ZW-ST-1201 |
| S020 | [HI-S020](requirements/stories/HI-S020.md) — Resolve actions into registered provider operations | ZW-ST-1302 |
| S021 | [HI-S021](requirements/stories/HI-S021.md) — Execute HA capability actions asynchronously | ZW-ST-1303, ZW-ST-1201 |
| S022 | [HI-S022](requirements/stories/HI-S022.md) — Provide shared action guard entry point | ZW-ST-1501, ZW-ST-1502, ZW-ST-1503 |
| S023 | [HI-S023](requirements/stories/HI-S023.md) — Persist append-only action audit evidence | ZW-ST-1504, ZW-ST-1601 |
| S024 | [HI-S024](requirements/stories/HI-S024.md) — Reject unsupported and invalid actions | ZW-ST-0202, ZW-ST-1503 |
| S025 | [HI-S025](requirements/stories/HI-S025.md) — Define provider interface and mock provider | ZW-ST-1302 |
| S026 | [HI-S026](requirements/stories/HI-S026.md) — Add mock switch, curtain and temperature sensor | ZW-ST-1302 |
| S027 | [HI-S027](requirements/stories/HI-S027.md) — Verify provider contracts with mock devices | ZW-ST-1302 |
| S028 | [HI-S028](requirements/stories/HI-S028.md) — Expose canonical home-state query API | ZW-ST-0301, ZW-ST-1501 |
| S029 | [HI-S029](requirements/stories/HI-S029.md) — Expose governed action-task API | ZW-ST-1201, ZW-ST-1503 |
| S030 | [HI-S030](requirements/stories/HI-S030.md) — Verify canonical read and action smoke flows | ZW-ST-1303, ZW-ST-1601 |

## Existing Engineering Work

REQ-003 remains the GoalAgent delivery/review record; home runtime work is not appended wholesale into it. Reuse its completed identity/RLS/audit patterns and explicitly link any runtime dependencies when admitting action stories. REQ-004 owns generic tool-side auth hardening; home-tool registration must align with it. REQ-005/006 own incremental CI and module boundaries. REQ-007/008/009 own cost/privacy/child-safety work. REQ-010 owns real-node deployment/recovery validation. REQ-011 records the original Home Intelligence handover; REQ-012 records this new planning documentation delivery. None is marked done by this PR.

## Scope Adjustments from the Prompt

- Do not create duplicate ADR-001/002/003: existing ADR-016 and ADR-010 already decide the requested subjects.
- Retain RabbitMQ platform tasks; MQTT remains a device-side transport. ADR-006 metadata reconciliation is recorded, not silently accepted.
- Preserve existing asynchronous task APIs and confirmation even where the source uses a simple POST /actions or basic R1 guard.
- Use a rebuildable in-memory current-state cache only; audit, confirmations, tasks and idempotency remain durable.
- Keep all new stories draft until normal Harness admission. No implemented backend increment was proven complete from the frontend prototype.
- Correct the suggested critical path: schemas can ship before live HA, Mock Provider requires those contracts, and validation/guard/audit precede enabled physical dispatch.
