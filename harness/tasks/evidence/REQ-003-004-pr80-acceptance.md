# REQ-003/004 shared prerequisite increment — human acceptance and merge

[human-001][2026-11-14] Instructed “no more findings. merge PR and do ledger
and housekeeping in another PR”. This accepts the bounded shared prerequisite
specification, proposed TC text/code/runtime and G1/M1/M2/I1–I6 dispositions
in PR #80. It supersedes historical draft TC and pending final acceptance
statements for this increment only. The supplied local pre-review remains
non-signing; no independent evaluator identity or T03/T07/T10/T13 signature
is invented. Generator authorship remains generator-001.

## Exact merge

[PR #80](https://github.com/rushwing/ai-family/pull/80) was marked ready and
squash-merged with expected-head matching from
[`9ac09b7fa3c02663442585f91360298472d0594a`](https://github.com/rushwing/ai-family/commit/9ac09b7fa3c02663442585f91360298472d0594a)
as [`9315763c071ca90c4f4a07226a6036b9c592dec2`](https://github.com/rushwing/ai-family/commit/9315763c071ca90c4f4a07226a6036b9c592dec2)
at 2026-11-14T05:55:29Z. GitHub closed/merged state, merge SHA and timestamp
were read back. Its base was `fec13be`, the REQ-038 housekeeping main.
This separate `chore/req003-004-pr80-ledger-housekeeping` branch starts from
that merged main and is left unmerged for review.

## Accepted scope and verification

The accepted increment supplies migration 0006 extending shared confirm_token
without changing legacy check-in semantics, atomic PostgreSQL proof nonce claim
plus token issuance, exact member/session/tool/payload binding, database-clock
expiry and one-winner consumption. Stored tokens are hashed. Independent
connections/processes reject proof/token replay; failures do not fall back
to memory. The registered home.execute_action boundary requires durable
confirmation plus an authenticated wrapper; missing wiring remains unavailable.
The wrapper rechecks JWT/current policy and supplies transaction-local member
RLS to its trusted handler. No provider or production home guard is connected.

[Final-head CI run 43563104147](https://github.com/rushwing/ai-family/actions/runs/43563104147)
completed with **14 successful jobs and 2 expected path-filter skips**.
PG16 MCP, GoalAgent, database integration and governance passed; fabric,
shared-schema and API matrices passed on Python 3.12/3.13/3.14. Web and
requirements skips were unrelated path skips, not required-case skips.
Downloaded MCP JUnit contains **156 cases: 142 passed, 14 legacy external
service skips**. The strengthened result gate passed against that artifact:
all **63 pinned identities** (20 confirmation, 43 home cases) appeared exactly
once and passed. Artifact SHA-256:
`3e5a3d76b651fc3e5bfb7320d47e3a813c29f0ac5eda3124554188aa23364faf`.

[Fix execution and dispositions](REQ-003-004-prerequisite-fixes.md) and
[fix provenance](REQ-003-004-prerequisite-fixes-provenance.json) pin runtime
commit `ac49fc9`, changed-source hashes, all 63 identities, local JUnit digest
and rebuilt gateway sdist/wheel-from-sdist hashes. Final pre-merge head
`9ac09b7` adds documentation only. Local execution: Linux aarch64, CPython
3.12.12, PG17.12, psycopg 3.3.9; 142 MCP passed / 14 legacy skips, 8 result-gate
unit tests, governance/21 planning regressions, Ruff, public-data and whitespace
checks passed. Packaging builds do not certify installed-artifact runtime.
Fixture RS256 verification replaces external JWKS retrieval, not JWT checking;
no live IdP or production HA/device certification is claimed.

[Original handoff](REQ-003-004-prerequisite-handoff.md) and
[original provenance](REQ-003-004-prerequisite-provenance.json) retain source
`0599c9f`: 130 MCP passed / 14 legacy skips and the original 51 prerequisite
identities. Those hashes/counts remain historical, not verification of the
later fixes. Both provenance JSON files remain byte-identical to merged main.

## Findings and attribution

- G1: pin all original 51 identities plus 12 new cases in an explicit manifest;
  reject omissions, replacements, duplicates and nonpassing outcomes. Eight
  gate tests include every single-case omission and the two-case bypass probe.
- M1/M2/I6: record evidence acceptance and remaining T17 block; REQ-004 depends
  on REQ-003 and REQ-039 links PR #80.
- I1: the bounded authorized generator return does not erase earlier review
  findings, reset REQ-003 review_round 4 or complete unrelated work packages.
- I2: transaction-held grant/binding/availability checks must share a locking
  or version protocol with revokers. The real-PG fixture revokes after preflight;
  the handler locks/rechecks and denies before effects. Production composition
  remains REQ-039 work; member RLS/preflight alone does not close that race.
- I3: handler failures roll back business writes while confirmation stays
  consumed. Explicit re-confirmation UX and unknown-outcome reconciliation are
  documented; no durable task/delivery semantics are inferred.
- I4: minimum 24-hour nonce retention, daily operator maintenance, global
  issuance pause/drain, database-clock batches, capacity/lag monitoring and
  restricted runtime permissions are documented. No cleanup scheduler is installed.
- I5: database ValueError at connection/setup/query/commit becomes fixed
  ConfirmationUnavailable for issuance and consumption; eight fault cases pass.

The human-supplied pre-review could not execute the gateway/PG suite in its
Termux environment because dependencies/services were unavailable. Its static
checks and gate bypass probe are reviewer-attributed observations, not author
executions. The local pre-review expressly did not approve the delivery;
final acceptance comes from the subsequent explicit human merge instruction.

## Lifecycle and housekeeping boundary

TC-003-11 and TC-004-01/02 are **passing** under this human final disposition,
with unchanged generator authorship. Only this bounded increment is accepted.
REQ-003 and REQ-004 remain active **req_impl / generator-001** and are not
archived or marked done. Their full tool-handler migration, durable audit,
other work packages and existing BUG dispositions retain their own gates.
REQ-003 pr_number 20 remains its historical broader implementation reference;
the acceptance section links this increment's PR #80. REQ-004 pr_number is 80.

REQ-039 remains **blocked / human-001**, blocked-from req_review / planner-001.
Its block reason now records accepted shared prerequisites and the remaining
explicit human T17 design restoration. This merge instruction does not execute
T17, approve the guard's ACs or admit its implementation. Production policy,
current availability, canonical guard composition, durable governed tasks,
physical dispatch, deployment and Feature/Stage acceptance remain separate.

Housekeeping updates only acceptance/lifecycle text, passing TC metadata,
product/package delivery descriptions and superseding links on historical
Markdown, plus the isolated planning fixture's new ledger-link target. All
runtime/test sources (except that fixture navigation), CI, migrations, schemas, dependencies,
required-case manifest, planning index and historical evidence JSON remain
byte-identical to merged main. No new local runtime execution is claimed.
Governance/planning, public-data/requirements, local links and whitespace are
checked for this ledger; any remote checks are attributed to their own head.

Local housekeeping verification on 2026-11-14 passed: governance and all
21 planning regressions, legacy requirements, public-data and CI-wiring gates,
Ruff on the changed planning fixture, 105 local Markdown links, lifecycle
invariants and whitespace. Byte comparisons confirmed unchanged runtime, CI,
migrations, required-case manifest, planning index and historical evidence JSON.
