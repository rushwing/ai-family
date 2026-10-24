# REQ-035 implementation delivery for external combined review

## Authority and stopping boundary

On 2026-10-24 human-001 instructed “Continue to implement, stop after req_impl
and wawit for exiternal review.” This supersedes the earlier requirement-only
handoff and authorizes generator-001 to complete the corrected specification's
combined proposed TC text, TC code and runtime delivery. The sole
[REQ-035](../features/REQ-035.md) records `req_impl` / `generator-001`.

The authenticated query runtime already delivered and corrected in PR #71
fully supplies the admitted implementation scope. This increment verifies that
delivery against the corrected contract and records implementation completion;
it does not invent additional runtime changes or discard prior verification.
Keep draft [PR #71](https://github.com/rushwing/ai-family/pull/71), four unchecked
ACs, four implemented TCs and proposed ADR-017. Stop at `req_impl` for external
combined requirement/TC/runtime review. No independent T03/T07/T10/T13 signature,
`req_impl_review` transition, readiness, final acceptance, merge or deployment
is inferred.

## Delivered implementation and acceptance mapping

| Acceptance | Delivered behavior | Evidence for external review |
| --- | --- | --- |
| AC1 | Explicit FastAPI composition serves the five prefixed home/area/device/detail/snapshot routes. Typed models retain canonical projections; device detail includes state/capabilities and snapshot obtains one atomic whole-home state capture from the accepted service. | [App](../../../apps/home-intelligence-api/src/home_intelligence_api/app.py), [models](../../../apps/home-intelligence-api/src/home_intelligence_api/models.py), TC-035-01 HTTP projection assertions, [OpenAPI](../../../apps/home-intelligence-api/openapi.json). |
| AC2 | Pinned RS256 verification checks issuer/audience/required claims and maps one platform role. The accepted query service enforces exact subject/member/home/role grants. Authentication precedes home syntax diagnostics, then authorization precedes resource/filter diagnostics. Every HTTP test runs with the DNS/socket network guard. | [Verifier](../../../apps/home-intelligence-api/src/home_intelligence_api/auth.py), [HTTP tests](../../../apps/home-intelligence-api/tests/test_queries.py), [network guard](../../../apps/home-intelligence-api/tests/conftest.py), TC-035-02. |
| AC3 | Explicit missing/empty/uninitialized/offline/fresh/stale results, inclusive freshness boundary, server-owned clock and fixed 400/401/403/503/500 responses preserve canonical meaning and hide diagnostics. All responses have no-store/nosniff headers. | TC-035-03 exercises actual HTTP responses, including clock failures, query configuration failures, redacted unexpected errors and rejected client controls. |
| AC4 | Required imports/skips fail the API suite. Ruff/strict mypy, checked-in/generated OpenAPI equality, direct/sdist-derived installs, normal/optimized smokes and dependency-sensitive Python 3.12/3.13/3.14 CI are delivered. | TC-035-04, [artifact builder](../../../apps/home-intelligence-api/tests/build_artifacts.py), [installed smoke](../../../apps/home-intelligence-api/tests/artifact_smoke.py), provenance and CI below. |

The TC text remains generator-authored and `implemented`, not independently
approved or `passing`. The [earlier handoff](REQ-035-review-handoff.md) preserves
all F1–F9 dispositions and historical source/verification limits.

## Source-specific verification

The runtime and tests were completed in repair commit
`4157d6dcff4882e14f1dcb942287709c42691706`. Documentation head
`4af218166b89e7bb678486b1003459f1740c7755` changes only the earlier evidence.
[CI run 40056835495](https://github.com/rushwing/ai-family/actions/runs/40056835495)
completed successfully for that exact head: **14 successful jobs, two
path-filter skips**. API, shared-schema and fabric jobs passed on Python
3.12/3.13/3.14, including required runtime tests and installed artifacts.
The two skips are unrelated web and legacy-workbook jobs, not acceptance tests.
The source repair's [CI run 40056570811](https://github.com/rushwing/ai-family/actions/runs/40056570811)
also completed successfully; the temporary governance-status reporting lag
captured in the older handoff has cleared.

Local Linux aarch64 / CPython 3.12.12 verification of the same runtime reports
**186 API tests, zero errors/failures/skips**, Ruff and strict mypy success,
21 passing planning regressions, and passing governance/public-data/legacy
requirement/secret/whitespace checks. One Starlette TestClient/httpx deprecation
warning is recorded, without skipped cases.

The recorded JUnit cases map to TC markers as follows: TC-035-01 **4**,
TC-035-02 **145**, TC-035-03 **29**, TC-035-04 **8** (total **186**).

[Artifact provenance](REQ-035-review-fixes-artifact-provenance.json) records
the actual repaired source hashes, 186-case JUnit digest, package/dependency
hashes and four **34-check** isolated smokes: direct and sdist-derived API /
fabric / schema wheel triplets under normal and optimized Python. Each returns
OpenAPI SHA-256 `db213eaedc0ec8c42da2c97ecce8561ec8faf9866f5823e0dad4b81058811979`.
Before this implementation handoff every recorded source hash was compared
with the current files: **zero mismatches**. This is reuse of verified identical
source, not a claim that the old dirty-base manifest is a new clean build.

This handoff changes lifecycle/evidence/navigation and the planning fixture
needed to resolve the new evidence link. It does not change API/package/test
sources or artifact inputs. Run governance/planning and link checks for these
new documents; prior runtime/artifact results remain attributed above. The
PR body records the resulting handoff-head CI separately.

## Operational boundary

The [API README](../../../apps/home-intelligence-api/README.md) documents
composition, verified identity claims, immutable key/grant rotation, clock
domain, exact route/error contract, operator logging and rollback.
Live IdP/HA bootstrap, reconnect reconciliation, dynamic inventory/policy,
provider execution/device writes, frontend wiring, durable confirmation/audit/
tasks, deployment, Windows/Termux certification and Feature/R1 acceptance are
outside this delivery. External review and final human acceptance remain open.
