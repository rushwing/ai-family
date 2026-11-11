# REQ-038 external combined review handoff

Historical implementation/review record. The later human final disposition in
[final acceptance](REQ-038-review-acceptance.md) supersedes pending approval,
draft states and req_impl stopping statements below; source-specific evidence
remains historical.

Prepared on 2026-11-11 for [draft PR #78](https://github.com/rushwing/ai-family/pull/78).
Implementation baseline: `545be9691db56813208b317e8f2300ef5c5be5c0`, based on
merged main `117b94fb29a2398be5be7e9fec693cee69ce76dc` (PR #77).
Commit `9e0ae41` adds documentation-only delivery evidence. The later
[pre-review follow-up](REQ-038-pre-review-fixes.md) changes the defensive entry
lookup and adds a regression; the baseline counts/hashes below are historical,
not verification of the revised runtime.

Human-001 authorized combined specification, proposed TC criteria, runtime
and verification with an explicit stop at `req_impl` for external review.
The sole [REQ-038](../archive/done/features/REQ-038.md) remains
`req_impl / generator-001`, AC1–AC4 unchecked; all four TCs remain
generator-authored drafts. This packet supplies no independent TC approval,
evaluator signature or lifecycle transition. Review criteria independently
before judging their implementation mappings.

| Proposed criteria | Review focus | Baseline JUnit mappings |
| --- | --- | --- |
| [TC-038-01](../test-cases/TC-038-01.md) | Exact switch/curtain plans, grouped resources, canonical correlation and real inference composition | 6 |
| [TC-038-02](../test-cases/TC-038-02.md) | Validation ordering, binding/instance isolation, fixed descriptors and hostile/missing maps | 51 |
| [TC-038-03](../test-cases/TC-038-03.md) | Plain JSON bounds, detachment, privacy, immutability, concurrency and zero effects | 39 |
| [TC-038-04](../test-cases/TC-038-04.md) | Missing/broken/methodless runtime, required skips, CI wiring and installed artifacts | 11 |

Counts overlap and are not independent approvals or unique-case totals.

Read [action_resolution.py](../../../toolsets/iot/home-device-fabric/src/home_device_fabric/action_resolution.py),
[source tests](../../../toolsets/iot/home-device-fabric/tests/test_action_resolution.py),
[gate probes](../../../toolsets/iot/home-device-fabric/tests/test_gate.py),
[installed smoke](../../../toolsets/iot/home-device-fabric/tests/action_resolution_artifact_smoke.py)
and [CI wiring](../../../.github/workflows/ci.yml) against the REQ contract.
The resolver uses package-private REQ-032 bounded helpers and accepted REQ-037
validation without modifying either. The exact initial descriptors and fixed
REQ-033 map shapes deliberately prevent arbitrary custom/provider operations.
The reviewer should assess this explicit version-1 compatibility boundary.

[Implementation evidence](REQ-038-runtime-implementation.md) records 2,162
full fabric cases with all eighteen required-runtime flags, no skipped cases,
97 resolver cases, Ruff, strict mypy and governance/21 planning regressions.
[Provenance](REQ-038-artifact-provenance.json) identifies the clean source,
JUnit digest, artifacts and official dependency digests. Both wheel pairs
passed normal/optimized isolated smokes, including four resolver runs with
27 explicit checks each. [Six killed mutations](REQ-038-mutations.json) bind
the same runtime/test hashes. These are generator checks, not independent review.

No operation description is a permission token. Private adapter exports must
not enter public responses/logs. The caller must enforce current configuration
and availability plus identity/member policy, confirmation, audit and governed
durable tasks before dispatch. No provider call or physical write is enabled.
The reviewer should identify reviewed commit, approve or revise criteria,
assess AC1–AC4 and record findings, execution and environment limits.
Keep readiness, final acceptance and merge separate from this delivery.

## Independent review still required (O4)

Human-001 supplied a local pre-review explicitly without an independent
signature or approval. Its informational observations and generator dispositions
are tracked in the [follow-up](REQ-038-pre-review-fixes.md). The four draft TCs
must still be reviewed against the REQ before judging implementation coverage.
An external evaluator must record the exact reviewed head and:

- Approve or revise TC-038-01's exact plans, grouped targets and correlation criteria.
- Approve or revise TC-038-02's ordered failures, exact maps and defensive-entry criteria.
- Approve or revise TC-038-03's bounds, privacy, isolation and effect-denial criteria.
- Approve or revise TC-038-04's mandatory-runtime, artifact and mutation criteria.
- Assess AC1–AC4 against those reviewed criteria, identify executed checks and
  environment limits, and record findings and their disposition.

Generator self-checks cannot complete these review actions. The REQ owner/status,
draft TC states, unchecked ACs and draft PR remain unchanged pending that handoff.
