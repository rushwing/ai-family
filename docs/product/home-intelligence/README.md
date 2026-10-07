# Zhiwei · Home Intelligence

Home Intelligence adds household state, vendor-neutral capabilities, workflows and governed reasoning to the existing ai-family platform. The current Web application is a fictional-data prototype; real household integration is the active R1 planning direction.

## Read in This Order

1. [VISION.md](VISION.md): long-term purpose and safety principles.
2. [ROADMAP.md](ROADMAP.md): R1–R12 outcomes, Now / Next / Later.
3. [CURRENT_STATE.md](CURRENT_STATE.md): source evidence, dependency-ready candidates and first coding Story.
4. [requirements/README.md](requirements/README.md) and [index.json](requirements/index.json): hierarchy, metadata, admission and detailed Features/Stories.
5. [ARCHITECTURE_ALIGNMENT.md](ARCHITECTURE_ALIGNMENT.md), [NFR.md](NFR.md), [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md): existing architecture and common constraints.
6. [CROSSWALK.md](CROSSWALK.md): source IDs, legacy ZW coverage and Harness integration.
7. Legacy context: [HANDOVER.md](HANDOVER.md), [PRD.md](PRD.md), [ARCHITECTURE.md](ARCHITECTURE.md), [PROJECT_MANAGEMENT.md](PROJECT_MANAGEMENT.md), [requirements.xlsx](requirements.xlsx), [roadmap.yaml](roadmap.yaml).

## Canonical Sources

| Information | Authority |
|---|---|
| Current product direction and capability stages | VISION.md / ROADMAP.md |
| Detailed new R1 backend and R2 Feature scope | requirements Feature/Story Markdown |
| New planning navigation projection | requirements/index.json; synchronize with Markdown |
| Existing UI interaction rules | PRD.md |
| Historical product/UI baseline | requirements.xlsx + same-version roadmap.yaml |
| Legacy overlap and refinement | CROSSWALK.md |
| Approved engineering ownership, lifecycle, acceptance evidence and review | Harness REQ/TC/BUG frontmatter and gates |
| Architecture decisions | Existing docs/adr/ records |
| Portfolio dates/releases and display state | GitHub Project, synchronized one-way from Harness |
| Implementation and delivery | PR / CI / Release; task_id / trace_id evidence |

## Change Rules

New planning uses Vision → R Stage → Feature → Story. Persistent implementation Tasks and new R2+ Stories are excluded. Preserve historical IDs; use CROSSWALK when scope overlaps. Before coding, admit a Ready Story to the existing Harness and obey its owner/status gate. Architecture changes require an ADR review first. Do not create a second editable engineering state machine or reverse-sync GitHub into Harness.

This documentation delivery is [REQ-012](../../../harness/tasks/features/REQ-012.md); the prior handover remains [REQ-011](../../../harness/tasks/features/REQ-011.md). Legacy workbook changes still require matching roadmap.yaml changes and its existing validator.
