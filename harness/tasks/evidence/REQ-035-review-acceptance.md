# REQ-035 / HI-S028 final acceptance and merge

[human-001][2026-10-24] Instructed “Merge PR and do ledger and housekeeping in
another PR”. This final disposition accepts AC1–AC4 and the combined
TC-035-01–04 text/code/runtime delivery, including F1–F9 and G1/G2 repairs and
the disclosed G3/G4 limits. It supersedes historical requirement-review and
req_impl stopping boundaries, unchecked ACs, implemented TCs, draft status
and pending final acceptance. Human-supplied local reports remain non-signing;
no independent evaluator identity or T03/T07/T10/T13 signature is invented.

## Exact merge and verification

[PR #71](https://github.com/rushwing/ai-family/pull/71) was marked ready and
squash-merged with exact-head matching from
`f5d9814db25c81d2bf6538b943f85fc54c0071f7` as
`b7e4e9ec3b68b5651885119183ebedb5d50f15f9` at 2026-10-24T03:53:31Z.
GitHub merged state and merge identity were read back; the separate
`chore/req035-acceptance-housekeeping` branch starts from that merged main.

[Final-head CI run 40059412181](https://github.com/rushwing/ai-family/actions/runs/40059412181)
completed successfully for the exact final implementation head: **14 successful
jobs, two path-filter skips**. API, fabric and shared-schema tests and installed
artifacts passed on Python 3.12/3.13/3.14. Web and legacy-workbook jobs were
unrelated path-filter skips, not skipped acceptance cases.

Latest [implementation evidence](REQ-035-runtime-implementation.md) and
[implementation-review artifact provenance](REQ-035-impl-review-artifact-provenance.json)
record Linux aarch64 / CPython 3.12.12 verification: **187 API tests**, zero
errors/failures/skips; TC counts **4/146/29/8**; Ruff and strict mypy success;
21 planning regressions and governance/public-data/legacy requirements,
secret/link/whitespace checks passing. One Starlette TestClient/httpx
deprecation warning remains recorded without skipped cases.

Four isolated normal/optimized direct/sdist-derived installs of API/fabric/
schema triplets each pass **36 checks**, including malformed-path authentication
ordering. All return OpenAPI SHA-256
`db213eaedc0ec8c42da2c97ecce8561ec8faf9866f5823e0dad4b81058811979`.
The manifest explicitly records dirty base `1a9f89f9`, hashes of the actual
repaired inputs, 187-case JUnit digest and artifact/dependency hashes. Every
recorded source hash matched the delivery before committing. The dirty base
is not relabeled as a clean build or substituted for final-head CI.

[Earlier repair provenance](REQ-035-review-fixes-artifact-provenance.json)
preserves the preceding 186-case, four 34-check repair source; the
[historical manifest](REQ-035-historical-artifact-provenance.json) preserves
the original dirty-base 157-case/four 25-check source. Neither older result
is presented as a run of the final amended implementation.

## Findings and attribution

F1–F9: home syntax is validated after authentication and before grant lookup;
well-formed unauthorized homes remain 403. Audience accepts the configured
string or a string list containing it; HTTPS issuer and mandatory signed
`iat`/`family_member_id` requirements are explicit. Path-ID schema and per-route
404 declarations match runtime, no automatic 422 appears, DNS/socket guards
cover request-time absence of provider/HA I/O, CI claims identify actual heads,
and query `invalid_configuration` remains fixed 503. The
[requirement handoff](REQ-035-review-handoff.md) preserves the detailed history.

G1 adds explicit malformed-device-path 401/400 source and installed regressions.
G2 documents the concrete store's fixed-inventory/state-row invariant; its
constructor creates an uninitialized row per device and public operations
retain those rows. G3/G4 remain attributed verification and authority limits,
not implementation defects or independent approval.

The supplied Termux/Python 3.14 pre-review could not install FastAPI/PyJWT or
run Ruff/mypy; it relied on Linux CI. Do not infer a new Termux/Windows, live
IdP/HA, physical-device, deployment or long-running certification from these
results. Current source/artifacts were generator-verified; final acceptance
comes from the explicit human merge instruction.

## Ledger disposition and housekeeping scope

T15: the sole [REQ-035](../archive/done/features/REQ-035.md) is archived as
done / human-001, review_round 0, pr_number 71, four checked ACs and four passing
TCs. Actual TC authorship remains generator-001. No pending or linked unresolved
req_bug blocks done. ADR-017 remains proposed under its separate decision gate;
the ledger invents no architectural or independent evaluator approval.

This separate housekeeping PR repairs archive links, delivery descriptions and
isolated planning fixtures. Historical evidence Markdown changes only REQ
navigation; historical JSON, runtime/test sources, dependencies and CI remain
identical to merged main. No new local runtime execution is claimed by this
ledger. Governance/planning, public-data/requirements, links and whitespace are
checked for this PR; any new CI execution is attributed to its own head.

Live IdP/HA bootstrap, reconnect reconciliation, dynamic inventory/policy,
device writes, durable services, frontend wiring, deployment, BUG-033 and
Feature/Stage acceptance retain separate gates. This instruction admits no
next implementation. The housekeeping PR remains unmerged for review.
