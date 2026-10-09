# REQ-014 — Combined TC and Runtime Self-check Evidence

Independent combined TC text/code and feature review is pending in [PR #29](https://github.com/rushwing/ai-family/pull/29). These are Generator self-checks, not T07/T10/T13 approval. Requirement authority: [REQ-014](../features/REQ-014.md).

## Tested Artifact and Environment

- Admission PR #28 merged as `9b62cbb`; TC design commit `4a87a8c`; test-first TC code `1000935`; implemented runtime/test artifact `b3fabd22db07833a37a38a59a53ac3307e8c1170`.
- Linux aarch64, Python 3.12.12; isolated `/tmp/req014-env` with editable shared package; pytest 9.1.1, Ruff 0.16.10 and mypy 2.4.0. No HA endpoint, credentials, hardware or provider service is required.
- Test-first execution: 475 existing shared-package cases passed; 180 binding cases skipped because the module was absent. Acceptance mode failed on these skips as intended. This is historical test-first evidence, not runtime acceptance.

## Runtime Results

```bash
/tmp/req014-env/bin/python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests \
  --require-inventory-runtime --require-binding-runtime -q --junitxml=/tmp/req014-results.xml
```

658 passed, 0 skipped, 0 failed. All 183 binding cases execute the real contract/test infrastructure, alongside 468 canonical inventory cases and 7 existing guard checks. JUnit results are local at `/tmp/req014-results.xml`; CI uploads `state-schema-tc-results`.

| TC | Executed / skipped / failed | Coverage |
|---|---|---|
| TC-014-01 | 7 / 0 / 0 | HA/mock shape and typed/JSON round trips, optional registry normalization, frozen nested records and detached snapshots; shape-only boundary. |
| TC-014-02 | 140 / 0 / 0 | Missing/type/version/provider/mapping errors, canonical vocabulary, complete entity mappings, mixed/unknown fields, deterministic paths and private value suppression. |
| TC-014-03 | 17 / 0 / 0 | Empty/partial collections, inventory reference integrity, non-Device IDs and cross-home rejection, provider-free canonical records and private inventory diagnostics. |
| TC-014-04 | 11 / 0 / 0 | Duplicate Device binding, same-instance resource collision, overlapping entity sets, distinct instances/provider namespaces and shared registry IDs. |
| TC-014-05 | 4 / 0 / 0 | Fictional HA-to-mock before/after comparison; full inventory/target equality, unchanged other binding and invalid-replacement input isolation. |
| TC-014-06 | 4 / 0 / 0 | Socket/DNS/process guards, filesystem-mutation guard, import/API boundary, missing-runtime and skip acceptance-mode failure. |

All tests call the delivered module. Parent guards reject attempted socket/DNS/process effects; the pure-validation case also guards filesystem writes. No live provider or dispatcher exists to fake into success. These are Python instrumentation boundaries, not proof of an OS-level sandbox.

## Other Validation

- Ruff on shared package source/tests: passed.
- Strict mypy on `libs/state-schema/src`: passed (3 source files).
- `bash scripts/check.sh`: all governance gates and 21 planning regressions passed.
- Public-data scan and legacy workbook/requirements checker: passed.
- `git diff --check`: passed.
- `uv build`: source distribution and wheel built successfully without new runtime dependencies.
- Wheel installed without dependencies in a separate `/tmp/req014-wheel-env`; smoke run from `/tmp` confirms installed HA/mock validation, stable canonical identity, Resting target resolution and invalid-version rejection.

## Review Boundary

The separate version-1 binding collection reads an inventory snapshot and exposes shape/reference validators and frozen models. It does not alter inventory, persist mappings, connect to HA, infer capabilities or dispatch actions. Fixture replacement compares data only. One Device has at most one binding per collection; resource uniqueness is local to provider kind/instance. Future providers or multi-provider selection require reviewed extensions.

The original author implemented the TC and feature code under human-001's explicit instruction to prepare one combined review. All TCs remain `implemented`; AC1–AC7 remain unchecked until the separate review accepts the evidence. The reviewer must examine TC text/code as well as the runtime, including constructors versus validated factories, diagnostic privacy and the absence/skip gates.

## CI

Implementation CI: [run 37760464531](https://github.com/rushwing/ai-family/actions/runs/37760464531), head `b3fabd22db07833a37a38a59a53ac3307e8c1170`. All six applicable jobs passed: governance-gates, changes, req002-integration, state-schema-tc, goal-agent and mcp-toolsets. The two unrelated web/requirements jobs were skipped by change detection; the required runtime suite had zero skipped tests. The T12 handoff is recorded in REQ-014. Final handoff documentation receives its own CI run.

## 2026-10-09 P1 Review Revision

Human-001 supplied a request-changes review: instance identifiers accepted endpoint/credential values. Revision on `feat/req-014-provider-binding`, based on `3528ac6`, committed as `fix(REQ-014): restrict provider instance aliases`. External factories now require `^[a-z][a-z0-9_-]{0,63}$`; the reason and structured path contain no supplied values. The contract and README specify nonsensitive local aliases with connection configuration stored separately. Syntax validation cannot identify arbitrary ID-shaped secrets.

Added 8 valid-alias cases to TC-014-01 and 48 rejection/privacy cases to TC-014-02. Both HA/mock providers exercise both factories and both validators; rejected values include user-info URLs, hostnames/IPs/ports, encoded URLs, credential assignments/Bearer/JWT forms, path/query/fragment syntax, controls, non-ASCII, uppercase, digit-leading and overlong IDs. Failure checks verify unchanged inputs, exact individual/collection paths, deterministic messages and absence of supplied values in string/repr/message diagnostics.

Local environment: Linux aarch64, Python 3.12.12, `/tmp/req014-env`, non-root UID 1000. The existing unreadable-file case executes normally.

```bash
/tmp/req014-env/bin/python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests \
  --require-inventory-runtime --require-binding-runtime -q --junitxml=/tmp/req014-p1-results.xml
```

714 passed, zero skips/failures. TC-014-01: 15 passed; TC-014-02: 188 passed; other TC counts unchanged (239 total binding cases). Ruff, strict mypy (3 source files), diff whitespace, all governance gates/21 planning regressions, public-data and legacy requirements checks passed. These results supersede the original runtime counts for this revision; historical artifact/CI results above remain unchanged. Independent acceptance of the fix is pending; PR #29 remains draft, TCs remain `implemented` and AC checkboxes remain unchecked.
