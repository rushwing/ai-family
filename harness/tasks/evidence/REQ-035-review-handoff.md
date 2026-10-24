# REQ-035 external requirement-review handoff

This file preserves the earlier requirement-review handoff and F1–F9 repairs.
The later 2026-10-24 instruction to complete implementation and stop at
`req_impl` supersedes its requirement-only boundary. See the current
[implementation delivery](REQ-035-runtime-implementation.md) and sole
[REQ](../archive/done/features/REQ-035.md) for current authority and verification.

## Authority and review scope

On 2026-10-24 human-001 instructed creating a PR for external `req_review`
after confirming requirement definition was prepared. The sole specification
is [REQ-035](../archive/done/features/REQ-035.md), now `req_review` / `evaluator-001`.
The separate external reviewer supplies the requirement disposition; this
preparation session supplies no independent signature or acceptance.

Review the REQ's contract, AC1–AC4, exclusions and review agenda together with
[proposed ADR-017](../../../docs/adr/ADR-017-home-query-http.md),
[API documentation](../../../apps/home-intelligence-api/README.md) and
[OpenAPI](../../../apps/home-intelligence-api/openapi.json).
Existing generator-authored source and implemented TCs are provisional
supporting material. They do not make requirement or implementation approval
implicit. ACs remain unchecked and ADR-017 remains proposed. No merge or
deployment is authorized by this handoff.

## Historical generator verification

Recovered 2026-10-23 JUnit files report 157 API, 1,888 fabric and 1,795 shared
schema tests, each with zero errors, failures or skips, on CPython 3.12.12 /
Linux aarch64. These are historical local results, not independent review.

[Historical artifact provenance](REQ-035-historical-artifact-provenance.json)
records the dirty base `8f35f331c9c2838ccc81d561040469f47d343758`, source and
artifact hashes, 157 API cases, and four 25-check installed smokes: direct and
sdist-derived distributions, each under normal and optimized isolated Python.
All four recorded the same OpenAPI digest. These were offline checks with
fictional inventory and ephemeral signing keys.

A 2026-10-24 comparison against that manifest found three changed inputs:
`apps/home-intelligence-api/README.md`,
`apps/home-intelligence-api/src/home_intelligence_api/app.py`, and
`apps/home-intelligence-api/tests/test_queries.py`.
The historical installed-artifact results therefore do **not** verify the
current delivery. Linux 3.13/3.14 and live HA behavior are not established by
these historical local results. Subsequent head-specific CI is recorded below.

## Current handoff checks

On 2026-10-24 API Ruff and strict mypy pass (four source files). Agent registry,
ADR, layout, planning, fabric CI wiring, legacy requirement, public-data and
migration RLS gates pass. These validate static consistency and review
navigation, not requirement acceptance or physical-device behavior.

The sandboxed HTTP suite timed out after 25 seconds. Repeating outside the
sandbox completed: **157 passed, zero skips/failures**, in 4.33 seconds:

```sh
timeout 60s /tmp/req035-env/bin/python -m pytest \
  -c apps/home-intelligence-api/pytest.ini apps/home-intelligence-api/tests \
  -q --junitxml=/tmp/req035-review-api.xml
```

Starlette emitted one TestClient/httpx deprecation warning. No test was skipped.
The planning regression suite also passes: 21 tests and eight subtests. Secret
scan and staged whitespace checks pass. That source run does not update
historical artifact hashes or establish requirement acceptance.

## Verified CI for the reviewed head

GitHub confirms [CI run 40054546508](https://github.com/rushwing/ai-family/actions/runs/40054546508)
targets `2ac9ab5e92faa846d23097fadac01e0a2a360080`, the head assessed by the
human-supplied pre-review. All 14 applicable jobs succeeded; web and legacy
requirements jobs were skipped by change detection. The three API matrix jobs
(Python 3.12/3.13/3.14) include Ruff, mypy, required source tests, and direct /
sdist-derived installed artifact smokes. Thus API artifact/matrix checks for
**that head** are complete; the earlier pending claim is superseded.
That head's CI is distinct from historical dirty-base provenance and does not
certify subsequent repair sources. `347912d` belongs to the preceding REQ-034
delivery and is not REQ-035 CI provenance.

## Human-supplied pre-review and authorized repairs

On 2026-10-24 human-001 supplied the local report on `2ac9ab5e` and instructed
“Fix all findings”. The report explicitly supplies no independent
T03/T07/T10/T13 signature; its Termux/Python 3.14 environment could not install
FastAPI or rerun Ruff/mypy. Its runtime assessment relied on Linux CI. These
repairs retain `req_review` / `evaluator-001`, four unchecked ACs, implemented
TCs, proposed ADR-017 and draft PR #71. This author acts only on the explicitly
authorized repairs, not as the independent evaluator.

| Finding | Disposition and verification |
| --- | --- |
| F1 | Choose public home syntax validation after authentication and before grant lookup: malformed home → 400; unknown/unauthorized well-formed home → 403. Twenty regressions cover four malformed values across five routes, checking 401 without identity and 400 without any grant lookup. Existing unauthorized device/filter tests preserve 403 ordering. |
| F2 | Remove strict scalar-only audience matching. Accept the configured string or a nonempty string list containing it, consistent with gateway decoding. Test scalar, singleton and multiple audiences; reject empty, mixed-type, non-string and nonmatching audiences. Document in REQ/ADR/README. |
| F3 | Retain HTTPS-only issuer configuration without an HTTP development/internal exception. Document the difference from the gateway example; regressions reject HTTP and missing-scheme issuers using a valid RSA public key. |
| F4 | Document mandatory signed integer `iat` and nonempty `family_member_id` as stronger JWT verification requirements. Existing missing/type/empty-claim tests exercise fail-closed behavior. The trusted composition owner must configure and verify the target IdP mappings before deployment; offline tests do not confirm a live IdP. |
| F5 | Add the anchored canonical ID pattern to path `device_id` via FastAPI Path; preserve 400 and authentication/authorization ordering. Assert its exact OpenAPI pattern and regenerate the checked-in schema. |
| F6 | Declare 404 only for device listing and device detail. Assert its presence/absence per route, with no automatic 422. Installed smokes verify the same schema. |
| F7 | Replace the vacuous provider-call clause in AC2 with absence of request-time provider/HA network I/O. An automatic fixture denies DNS, connection and datagram socket operations throughout every HTTP test and fails teardown even if a handler catches the injected error. This covers accepted and rejected requests, not just one denial case. |
| F8 | Record the actual reviewed head's successful matrix/artifact CI above, separate from old dirty-base evidence; update the PR body to the repaired source and actual CI run. Repair-head CI is recorded separately once available. |
| F9 | Explicitly retain query-service `invalid_configuration` → 503 `state_unavailable` in REQ/README. A regression injects that error and asserts fixed body/no-store/nosniff; unexpected errors remain 500. |

Installed smokes additionally exercise malformed-home authentication ordering,
array audience compatibility, route-specific 404 and the anchored path pattern
in normal/optimized Python. All runtime/schema/TC changes remain provisional
supporting artifacts pending external requirement and later implementation
acceptance.

## Repair source verification

On 2026-10-24 / Linux aarch64 / CPython 3.12.12, the repaired source passes
**186 API cases, zero failures/errors/skips**, with the automatic network guard
active (4.81 seconds). One existing Starlette TestClient/httpx deprecation
warning remains. Ruff and strict mypy pass; `bash scripts/check.sh` passes
including all 21 planning regressions, as do public-data and legacy requirement
checks. Whitespace checks pass.

The current-source artifact builder completed successfully:

```sh
/tmp/req035-env/bin/python apps/home-intelligence-api/tests/build_artifacts.py \
  --out-dir /tmp/req035-review-fixes-artifacts \
  --test-results /tmp/req035-review-api.xml
```

[Repair artifact provenance](REQ-035-review-fixes-artifact-provenance.json)
records the dirty base `2ac9ab5e`, hashes for the actual repaired source,
186-case JUnit digest and built artifact/dependency hashes. All source hashes
were compared with the delivery before committing: zero mismatches.
Direct and sdist-derived triplets each pass **34 checks** under normal and
optimized isolated Python, all with generated OpenAPI SHA-256
`db213eaedc0ec8c42da2c97ecce8561ec8faf9866f5823e0dad4b81058811979`.
Dependencies are downloaded once; installation and smoke runs are offline.
The dirty base is not presented as a tested clean commit; repair-head CI is
recorded separately. No live IdP, private HA, Windows, Termux or deployment
certification is implied.

## Repair-commit CI

[CI run 40056570811](https://github.com/rushwing/ai-family/actions/runs/40056570811)
targets repair commit `4157d6dcff4882e14f1dcb942287709c42691706`.
The API, shared-contract and fabric jobs all completed successfully on Python
3.12/3.13/3.14, including their installed-artifact checks. Changes, GoalAgent,
MCP and database integration also completed successfully; web and legacy
requirements jobs were skipped by path filters. At evidence capture, the
governance job reported successful steps and conclusion with a completion
timestamp, but its top-level status still read `in_progress`; this is not
presented as a completed all-jobs run. PR checks provide the final-head status.

This evidence update changes only this Markdown record; repaired API source,
test/schema files and fresh artifact manifest remain the source verified at
`4157d6d`. Requirement approval and implementation acceptance remain pending.
