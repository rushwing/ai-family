# REQ-035 external requirement-review handoff

## Authority and review scope

On 2026-10-24 human-001 instructed creating a PR for external `req_review`
after confirming requirement definition was prepared. The sole specification
is [REQ-035](../features/REQ-035.md), now `req_review` / `evaluator-001`.
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
current delivery. Full current-source runtime and artifact verification remains
an implementation-review obligation; Linux 3.13/3.14 and live HA behavior are
not established by the historical local results.

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
scan and staged whitespace checks pass. Current installed-artifact verification
and CI outcomes remain pending; the fresh source run does not update historical
artifact hashes or establish requirement acceptance.
