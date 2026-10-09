# Requirements Operating Rules

## Read in This Order

[Vision](../VISION.md) → [active roadmap](../ROADMAP.md) → Feature → dependency-ready Story → [architecture](../ARCHITECTURE_ALIGNMENT.md), referenced ADRs, [NFR](../NFR.md) and [DoD](../DEFINITION_OF_DONE.md) → approved Harness REQ/TC → implementation and verification. The machine entry point is [index.json](index.json). The index lists local product dependencies; shared platform/runtime evidence prerequisites in a Story’s Technical Notes must also be satisfied before implementation or physical dispatch.

## Hierarchy

Vision → Roadmap Stage → Feature → Story. Implementation checklists remain inside the candidate Story before admission and its Harness REQ after admission. ADR, NFR, TC, BUG and DoD are cross-cutting engineering objects. No new persistent Task requirements are created.

## Authority and Legacy Integration

- VISION.md and ROADMAP.md define current household direction and R-stage outcomes. Feature Markdown defines product outcomes; unadmitted Story Markdown defines candidate scope and acceptance. On admission, move the detailed specification into its Harness REQ and replace the Story with navigation only. index.json is a navigation projection with matching identity metadata.
- The existing PRD remains authoritative for established UI behavior and prototype scope. The new architecture alignment records how the R1 backend connects to it.
- requirements.xlsx and roadmap.yaml remain the unchanged versioned legacy UI/product baseline. CROSSWALK.md identifies related ZW records and active slice coverage; existing IDs and historical statuses are preserved. Do not execute the overlapping legacy backend records as an independent second backlog.
- HI-* IDs identify new, narrower backend slices. F/S numbers from the input are source_ref labels, not competing primary IDs. Legacy refs indicate related scope, never an assertion that the whole older story is complete.
- Admitted engineering work is represented once by a Harness REQ. Its body and frontmatter exclusively own admitted scope, acceptance criteria, engineering dependencies, priority, owner, lifecycle, review rounds, TC/BUG gates, PR and completion. Do not maintain those fields/checklists in the admitted Story or index. GitHub receives a one-way management projection.

## Lifecycle and Admission

Stage and Feature states are planned, active, completed, paused or cancelled. Story planning states are draft, ready, active, blocked, done or cancelled. All initial HI stories are draft. Dependency-ready means dependencies are satisfied, not that engineering is authorized.

A Story becomes ready only after human-001 approves its scope and it meets Definition of Ready: stable parent, bounded independent outcome, explicit non-goals, verifiable acceptance, dependencies, risk, architecture references and verification environment. Aim for 0.5–3 developer-days; split excessive work without invented estimates.

Before coding, create a linked REQ using the next available repository ID, add reciprocal `story_ref` / `harness_ref`, move scope/acceptance/non-goals/verification into the REQ, and follow the existing owner/status handoff gate. Use the admitted Story template for the remaining navigation record. Remove `status`, `priority` and `depends_on` from its frontmatter and index entry; engineering dependencies are REQ IDs in the REQ's `depends_on`. The original product parent/stage/legacy/source identity remains in the Story.

Read engineering status, owner, priority and dependencies directly from the active or archived REQ. `python tools/check_home_intelligence_planning.py` validates reciprocity and prints current admitted status without storing a second lifecycle. UI/Project consumers can map Harness draft -> draft (or ready after explicit scope approval), review/design/implementation states -> active, blocked -> blocked and done -> done, but must derive that view on read. Do not copy or hand-edit that projection in Story files or index.json. Cancellation/paused planning does not cancel an admitted REQ: human-001 records the engineering disposition. Archive moves must repair navigation links; the resolver supports `harness/tasks/archive/done/features/`.

Feature completion requires child acceptance and its demo exit criteria; Stage completion requires feature acceptance and stage exit evidence. No auto-completion from code presence, PR merge alone, or skipped required tests.

## Metadata and Synchronization

Feature and Story frontmatter uses JSON-compatible YAML scalars/lists. Required fields and examples are in the templates. IDs never change when sorting changes. index.json copies identity, title, product relationships and paths; unadmitted candidates also carry planning dependencies/state. Admitted entries retain only navigation metadata and the Harness reference. Synchronize it in the same PR as Markdown edits. Stage objects in the index match ROADMAP.md. The versioned `refinement_boundary` policy is fixed to the REQ-012 delivery: R1 active, R2–R12 planned, exactly ten R1 and ten R2 Features, and exactly thirty Stories all belonging to R1. The validator checks both the declared policy and its actual objects against this contract. Marking another stage completed does not authorize its Stories. Expanding refinement requires an explicit scope amendment and synchronized policy/validator change in a reviewed PR. Legacy workbook edits must continue to update the existing roadmap.yaml and pass its checker; this delivery leaves both unchanged.

## Traceability

Recommended commit title: `feat(HI-F004/HI-S012): add Positionable schema`. PR bodies include `Story: HI-S012`, `Refs: REQ-NNN`, TC evidence and relevant ADRs. Story → REQ → TC/BUG → PR → Release → task_id/trace_id supplies forward and reverse navigation. Code comments only carry Story IDs when they explain a durable constraint, not on every line. New files do not repeat every ancestor in their name.

## Initial Selection

HI-S008/009/010/011/012 are delivered through archived REQ-013/014/015/016 and [REQ-017](../../../../harness/tasks/archive/done/features/REQ-017.md). PR #34 merged as `0443b84`; human-001 accepted six initial Capability AC1–AC7 and TC-017-01–06 under the final merge/archive disposition. [Closeout evidence](../../../../harness/tasks/evidence/REQ-017-review-acceptance.md) records provenance and post-merge verification. Read owner/status directly from Harness. HI-S019 is admitted through [REQ-018](../../../../harness/tasks/features/REQ-018.md) for engineering delivery; independent implementation acceptance remains pending. HI-S001 and HI-S025 are candidates awaiting their own scope approval and admission; HI-S025 also requires the admitted action contracts to be delivered. HI-S012 now satisfies the schema prerequisite for HI-S015/022/024/026; their other dependencies and engineering admission remain required. HA tokens or physical hardware do not block offline contract/configuration work. See CURRENT_STATE.md for unresolved integration work.

## Templates

Use [FEATURE_TEMPLATE.md](FEATURE_TEMPLATE.md) and [STORY_TEMPLATE.md](STORY_TEMPLATE.md). After admission use [ADMITTED_STORY_TEMPLATE.md](ADMITTED_STORY_TEMPLATE.md), which contains navigation only. These templates complement, rather than replace, harness/requirement-standard.md and harness/testcase-standard.md.

## Validation

Run `python tools/check_home_intelligence_planning.py` from the repository root (also included in CI and scripts/check.sh). Before review, validate reciprocal REQ identity, active/archive uniqueness and absence of copied engineering fields/checklists in admitted Stories, then IDs, file/index metadata, parents, stage links, feature child lists, dependencies, cycles, legacy references and local links. Assert 12 stages, 20 features, 30 R1 stories, no R2+ stories and no new persistent tasks. Run existing governance gates and the legacy workbook checker. Keep check commands and results in the PR; required runtime behavior is verified by future linked TC, not this documentation delivery.
