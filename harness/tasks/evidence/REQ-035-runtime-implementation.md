# REQ-035 implementation delivery for external combined review

The implementation pre-review follow-up below records the latest G1–G4
dispositions and supersedes the initial source counts and artifact hashes for
the updated files. Earlier source-specific results remain historical evidence.

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

## Initial source-specific verification

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

## Implementation pre-review follow-up: G1–G4

On 2026-10-24 human-001 supplied the non-signing report on implementation head
`1a9f89f9` and instructed “Fix all findings”. The report confirms F1–F9 remain
resolved and raises G1/G2 as hardening/documentation items; G3/G4 describe
verification and authority limits. Repairs remain generator-authored under
`req_impl` / `generator-001`, with unchecked ACs, implemented TCs, proposed
ADR-017 and draft PR #71. No acceptance or independent signature is inferred.

| Finding | Disposition |
| --- | --- |
| G1 | Add an explicit HTTP regression for `/api/devices/INVALID?home_id=home-example`: absent token → fixed 401; valid token and authorized home → fixed 400. Existing unauthorized-home cases preserve 403 before malformed device diagnostics. The installed smoke exercises both new requests under normal/optimized Python as well. |
| G2 | Confirm and document the existing store invariant in REQ/README and the detail route: the concrete HomeQueryService uses one CurrentStateStore; its constructor creates a state row for every fixed inventory device. Public operations retain those rows. A found device has a StateView even with no observations; separate inventory/state registration and private mutation are unsupported. Runtime behavior is unchanged. |
| G3 | Preserve the reviewer’s actual limitation: the supplied Termux/Python 3.14 report could not install FastAPI/PyJWT or run API/Ruff/mypy checks. This is not treated as a local pass. Validation below is attributed to Linux aarch64/CPython 3.12 and the PR’s Linux CI matrix; no Termux or live IdP/HA certification is inferred. |
| G4 | Preserve human-authorized combined delivery and the absence of independent T03/T07/T10/T13 approval. External evaluator disposition and final human acceptance remain pending; this repair session does not self-sign them or move beyond req_impl. |

The [accepted store constructor](../../../toolsets/iot/home-device-fabric/src/home_device_fabric/state_store.py)
allocates rows from each inventory’s devices, and inventory reads remain fixed
for the store lifetime. The [accepted query service](../../../toolsets/iot/home-device-fabric/src/home_device_fabric/home_queries.py)
uses that same store for both device and state lookup. Neither shared package
is modified by this repair.

Latest local source verification: Linux aarch64 / CPython 3.12.12, **187 API
cases, zero failures/errors/skips**, with the automatic network guard active
(5.43 seconds). Marker counts are TC-035-01 **4**, TC-035-02 **146**,
TC-035-03 **29**, TC-035-04 **8**. Ruff, strict mypy, all governance gates,
21 planning regressions, legacy requirements, public-data and whitespace
checks pass. One existing Starlette TestClient/httpx deprecation warning
remains. Test command:

```sh
timeout 60s /tmp/req035-env/bin/python -m pytest \
  -c apps/home-intelligence-api/pytest.ini apps/home-intelligence-api/tests \
  -q --junitxml=/tmp/req035-review-api.xml
```

The updated artifact builder passes with the same JUnit file:

```sh
/tmp/req035-env/bin/python apps/home-intelligence-api/tests/build_artifacts.py \
  --out-dir /tmp/req035-impl-review-artifacts \
  --test-results /tmp/req035-review-api.xml
```

[Implementation-review artifact provenance](REQ-035-impl-review-artifact-provenance.json)
records dirty base `1a9f89f9`, actual updated source hashes, the 187-case JUnit
digest and artifact/dependency hashes. All recorded source hashes match the
delivery: zero mismatches. Four isolated direct/sdist-derived normal/optimized
smokes each pass **36 checks**, including malformed-path 401/400 ordering.
OpenAPI remains unchanged, with SHA-256
`db213eaedc0ec8c42da2c97ecce8561ec8faf9866f5823e0dad4b81058811979`.
The dirty base remains explicit; new repair-head CI is reported separately
in the PR body and is not attributed to the earlier reviewed head.
