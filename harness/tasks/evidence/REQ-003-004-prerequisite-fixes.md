# PR #80 local pre-review fixes

Historical source-specific delivery record. The later
[human bounded acceptance and merge](REQ-003-004-pr80-acceptance.md) supersedes draft TC, pending
acceptance and unmerged-PR statements for this increment. Full REQ-003/004
completion, an independent evaluator signature and REQ-039 T17 restoration
are not asserted. Execution counts and source hashes below remain historical.


Generator-001 delivered the human-requested fixes at `ac49fc9b5bbed8e60b6fdd2abd5d010a59e50723`.
The supplied local pre-review is not an independent review signature. REQ-003
and REQ-004 remain req_impl / generator-001; all proposed TCs remain draft;
REQ-039 remains blocked / human-001 pending independent review and human T17.

| Finding | Resolution |
| --- | --- |
| G1 | Explicit required-case manifest retains all original 51 identities and adds 12 regressions. Every identity must appear exactly once and pass; missing, renamed, duplicated and nonpassing cases fail. CI watches the manifest. Eight gate tests include omission of each required identity in turn and the original two-case bypass probe. |
| M1 | REQ-039 now records attached implementation/evidence pending independent review and T17. Baseline inspection statements are marked historical; no unblock is inferred. |
| M2 | REQ-004 depends_on includes REQ-003. |
| I1 | REQ-003 records the bounded human-authorized return to generator ownership; review_round stays 4, prior findings and unrelated work packages remain in force. PR #20 stays historical; this increment is PR #80. |
| I2 | README and the REQ-039 handoff require handler-transaction grant/binding/availability checks with locks/versioning shared by revokers. A real-PG fixture revokes after the final preflight read; the handler locks/rechecks and denies before effects. Handler ToolDenied preserves redacted 403 and rolls back. Production policy design remains REQ-039 work. |
| I3 | Three regressions prove handler denial/unavailability/unexpected failure rolls back database writes while confirmation stays consumed. README specifies fresh explicit confirmation, failure UX and unknown-outcome reconciliation. |
| I4 | README gives 24-hour minimum nonce retention, daily operator maintenance, global issuance pause/drain, database-clock batch pruning, capacity/lag monitoring and no runtime DELETE grant. No scheduled cleanup service is claimed. |
| I5 | Only ProofReplay escapes transaction normalization. Eight fault injections cover ValueError at connection/setup/query/commit for issuance and consumption; all produce fixed ConfirmationUnavailable. |
| I6 | REQ-039 pr_number is 80; REQ-004 also links the combined delivery. |

## Executed evidence

- Full MCP suite: **142 passed, 14 legacy external gateway/IdP skips**.
- Required manifest: **63 passed**, comprising 20 confirmation and 43 home
  cases (original 51 plus 12 regressions); no required skips/errors/failures.
- Required-result gate against the final JUnit: passed; gate unit tests: 8 passed.
- Governance checks, including 21 planning regressions, Ruff, public-data scan
  and whitespace checks passed. Final documentation was checked again before push.
- Gateway sdist and wheel-from-sdist rebuilt successfully. These are packaging
  checks, not installed-artifact runtime certification. Goal MCP code did not change.

[Fix provenance](REQ-003-004-prerequisite-fixes-provenance.json) pins this source
commit, changed-source hashes, 63 passing identities and rebuilt artifact hashes.
Local JUnit: `/tmp/req003-004-fixes-results.xml`; artifacts:
`/tmp/req003-004-fixes-artifacts/`. Local environment: CPython 3.12.12,
PostgreSQL 17.12, psycopg 3.3.9, Linux aarch64; fixture RS256 JWT verification.
PostgreSQL 16 remote results for the final PR head are attached to PR #80 after
CI execution. The [original handoff](REQ-003-004-prerequisite-handoff.md) and
provenance remain unchanged as historical evidence for their pinned commit.
