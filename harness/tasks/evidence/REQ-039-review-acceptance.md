# REQ-039 / HI-S022 final acceptance and merge

[human-001][2026-11-14] Instructed “Merge Pr and do ledger and housekeeping
in another PR”. This final disposition accepts AC1–AC8 and the combined
TC-039-01–04 text/code/runtime delivery, including F1–F5 fixes and I1–I16
dispositions. It supersedes historical req_impl stopping boundaries,
unchecked ACs, draft TCs, draft PR and pending final acceptance. The supplied
local pre-reviews remain non-signing; no independent evaluator identity or
T03/T07/T10/T13 signature is invented. Authorship remains generator-001.

## Exact merge

[PR #82](https://github.com/rushwing/ai-family/pull/82) was marked ready and
squash-merged with expected-head matching from
[`532d058c2b59b9576545c22625a979d43c1327a1`](https://github.com/rushwing/ai-family/commit/532d058c2b59b9576545c22625a979d43c1327a1)
as [`e0f3a7e0ad4c19ffbc615a548b59cff740f62a47`](https://github.com/rushwing/ai-family/commit/e0f3a7e0ad4c19ffbc615a548b59cff740f62a47)
at 2026-11-14T08:09:02Z. GitHub merged state, merge SHA and timestamp were
read back. Its base was `382ebbb`, the shared-prerequisite ledger main.
The separate `chore/req039-acceptance-housekeeping` branch starts from the
merged main and remains unmerged for review.

## Accepted behavior and verification

HomeActionGuard verifies the original RS256 bearer, exact scoped grants,
canonical action semantics and initial allowlist, binding/configuration
generation, independently aged availability and committed epoch. Final entry
rechecks under retained PG authority protections and the participating state
publication barrier, acquired DB before state. It composes existing durable
confirmation consumption; tokens stay consumed after final rejection.
Eligibility exports no permission token. Even eligible confirmed production
entry returns fixed 503 with zero task/provider calls. Single-store scope,
participating authority/state writers and finite waits remain required.

[Final-head CI run 43574016947](https://github.com/rushwing/ai-family/actions/runs/43574016947)
completed successfully: **14 successful jobs and 2 expected path-filter skips**.
PG16 MCP, GoalAgent, database integration and governance passed. Fabric,
shared-schema and API matrices passed on Python 3.12/3.13/3.14. The web and
requirements skips are unrelated path filters, not skipped required cases.

The downloaded MCP JUnit contains **242 cases: 228 passed, 14 legacy external
gateway/IdP skips, zero failures/errors**. The result gate was rerun against
that downloaded report: all **149 pinned identities** (63 existing shared
prerequisites and 86 guard cases) appeared exactly once and passed.
JUnit SHA-256: `83b8d48906c3d76a0e4480a14796609dfcb1c36806a93aae0e58078aecacabec`.
The downloaded guard artifact provenance records four fresh installed PG smokes,
direct and sdist-derived wheel sets, ordinary and optimized Python, **19 checks
each**, dispatch disabled. All **40 recorded artifact/dependency hashes** were
verified against the downloaded files. Provenance SHA-256:
`e08cac82146499089a51cb622402df0ce0fae4cc245af0e09d493ca406ab332f`.
That CI artifact records CPython 3.12.16 and GitHub's synthetic merge checkout
`d77a2d38c52e46008463a045adea5838b59607ec`; it belongs to the run associated
with PR head `532d058`, not a new local run or the later squash commit.

Historical [runtime handoff](REQ-039-runtime-implementation.md) and the sole
[artifact provenance](REQ-039-artifact-provenance.json) retain implementation
source `903e8138c0e593d1638580c4858b4b03fad67665`: Linux aarch64, CPython
3.12.12, PG17.12, 228 MCP passed / 14 legacy skips, 2,163 fabric passed with
zero skips, five killed mutations and four installed 19-check PG smokes.
Fixture RS256 verification substitutes external JWKS retrieval, not signature
checking. Source-specific evidence is not relabeled as final-head CI evidence
or live IdP/HA/device certification. Historical provenance JSON stays byte-identical.

## Findings and attribution

- F1: ordered failures deny unknown/ungranted targets before descriptive lookup;
  contradictory granted inventory/generation/binding becomes guard_unavailable.
- F2: finite validated reason/status vocabulary, post-grant semantic visibility
  and conservative wrapper error mapping preserve failure privacy.
- F3: declare direct Inventory and bounded JSON reuse dependencies.
- F4: the REQ links committed runtime/artifact evidence. Local governance and CI
  reject missing or untracked inline local links in active requirement files.
- F5/I16: remove the two orphan implementation-named evidence duplicates. Keep
  the single REQ-linked runtime/artifact pair and preserve historical local paths.
- I1–I6: explicit combined human authority supersedes the earlier design-only
  stop without independent signatures; retain the capture API, writer protocol,
  finite waits and single-store/distributed-authority boundary.
- I9/I10/I15: store-wide locking may block unrelated homes, and repeated preflight
  opens PG connections/authority leases. Future optimizations must preserve final
  entry guarantees; no optimization is delivered by this closeout.
- I13/I14: the link gate covers active requirement Markdown and requires Git
  metadata; evidence/TC/story links and source tarballs remain outside its scope.
  Archiving this REQ reduces its active scan from ten requirements to nine.
  I7/I8/I11/I12 require no behavior change under the supplied review disposition.

The human-supplied reviews and their limitations retain reviewer attribution.
Final acceptance comes from the later explicit human merge instruction, rather
than an invented independent evaluation or generator self-approval.

## Lifecycle and housekeeping boundary

T15: the sole [REQ-039](../archive/done/features/REQ-039.md) is archived as
**done / human-001**, review_round 0, pr_number 82, eight checked ACs and four
passing TCs. Generator authorship is unchanged. No pending or linked unresolved
req_bug blocks done. Full REQ-003 and REQ-004 remain req_impl / generator-001;
their broader work packages and historical findings are not closed.

The housekeeping PR updates acceptance/lifecycle text, archive navigation,
passing TC metadata, current delivery notes and the isolated planning fixture.
Historical Markdown adds only navigation or a superseding closeout link.
Runtime/test sources, CI, migrations, schemas, dependencies, required-case
manifest, planning index and historical evidence JSON remain identical to
merged main, except the planning fixture navigation. No new local runtime
execution is claimed. Housekeeping checks and remote CI are attributed to
their own head separately from the implementation evidence above.

Local housekeeping validation on 2026-11-14 passed: all governance gates,
21 planning regressions and two Harness-link regressions, legacy requirements,
public-data and CI-wiring checks, Ruff on the planning fixture, 136 local
Markdown targets, archive/AC/TC/bug invariants and whitespace. Byte comparisons
confirmed all 411 protected source/config/index/evidence files unchanged from
merged main, including all 53 historical evidence JSON files. The active link
gate passed against the staged archive move and all nine remaining requirements.

Production policy/administration, distributed authority, durable audit and
governed tasks/outbox/idempotency, provider dispatch, physical writes, live
IdP/HA/device certification, deployment and Feature/Stage acceptance retain
separate gates. No next implementation is admitted by this instruction.
