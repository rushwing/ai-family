# REQ-037 local pre-review dispositions

Human-001 supplied the local pre-review of PR #76 at
`121f9dad9c27a3c1c26cfbddee95bc0d42887693` and instructed “Fix all findings”.
The report explicitly disclaims independent review approval. This generator
follow-up preserves `req_impl / generator-001`, unchecked AC1–AC4, all four
draft TC documents and draft PR status.

| Finding | Disposition | Remaining review boundary |
| --- | --- | --- |
| F1 — missing REQ-032 dependency | Added REQ-032 to REQ-037 `depends_on`, matching the existing direct `_json` import and contract text. | Dependency is now explicit; no accepted dependency implementation changed. |
| F2 — draft TC criteria and acceptance pending | Kept all four TCs draft and the REQ at req_impl; the handoff still requests external review or revision of TC criteria before implementation acceptance. | External evaluator TC review and implementation acceptance remain pending. This local report and generator fixes cannot supply those signatures. |
| F3 — direct result construction | Retained the documented typed-record constructor. Clarified in the package README that checked results come from validate(), direct construction proves no validation, and status is not an authorization/dispatch credential. | No factory guard is introduced: it would not establish a security boundary for this internal typed record. Trusted caller policy and dispatch checks remain separate. |
| F4 — private `_json` helper | Documented package-internal reuse, the bounded JSON/encoding dependency, and the need to verify both mapping and action consumers when changing it. The helper remains private. | No new public helper/export contract or accepted-module refactor is introduced. |
| F5 — read-only defense in depth | Retained the existing all-read-only rejection before action lookup, including misdeclared setters and ack_only actions. The report requests no change. | Existing tests and reported probes remain evidence of current behavior, not independent acceptance. |

## Verification scope

Only dependency metadata and documentation change. Runtime, tests, schemas,
CI wiring, mutation evidence and artifact provenance retain the exact bytes
from the reviewed baseline. Existing full-suite/artifact results remain
source-specific evidence; they are not represented as newly executed checks.
The local pre-reviewer's excluded notes are not copied into the repository.

On 2026-11-11, planning/dependency/local-link validation and all 21 planning
regressions passed. Agent registry, seventeen-flag fabric CI wiring,
public-data, secret and whitespace checks passed. A diff against reviewed
baseline `121f9dad` confirmed that tracked changes are limited to the REQ,
README and handoff; this new disposition record is the only additional file.
Runtime, tests, schemas, CI and historical evidence are unchanged. Full runtime
and artifact checks were not repeated locally for this metadata/documentation
fix; any subsequent remote CI run is separate final-head validation.
