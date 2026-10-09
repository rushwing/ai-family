# REQ-017 — TC and Runtime Self-check Evidence

Authority: [REQ-017](../archive/done/features/REQ-017.md). Human-001 supplied PR #33's non-signing pre-review and explicitly authorized its merge, then TC/code/runtime delivery through req_impl and a stop for external review. This is Generator implementation evidence, not independent T07/T10/T13 approval. At the original implementation handoff, AC1–AC7 were unchecked and TC-017-01–06 implemented. Human final acceptance below supersedes that boundary; merge/done disposition is recorded in [closeout evidence](REQ-017-review-acceptance.md).

## Specification and Artifact Provenance

[PR #33](https://github.com/rushwing/ai-family/pull/33) merged at `2026-10-09T05:34:42Z`: final head `52c97ec1a037490e7680c45875e509f86047261a`, squash `d6097832ade46f31c6bb5a439deac6411469a69f`. [CI run 37888988398](https://github.com/rushwing/ai-family/actions/runs/37888988398) passes seven applicable jobs, with three path-filtered skips. Q1–Q5 and the human scope/proceed disposition are in the merged specification. The supplied Termux / CPython 3.14.6 1296-test and independently reconstructed specification matrix results verify that earlier documentation artifact; they are not author-performed runs or evidence for this new runtime.

Test-first artifact: `278be16`. With the initial module absent, the existing suite passes 1296 and all 197 new cases explicitly skip. New required mode exits 4 with missing-runtime diagnostics; existing `--require-capability-runtime` mode also exits 1 when the 197 required cases skip. Existing base Capability presence cannot hide missing initial-catalogue work. The isolated acceptance probes later exercise both real pytest gates.

Final runtime/source/test artifact: `c1901bf999ac1d40842bbffffb3c990fb1af5b52`. Final source/test checks ran immediately before that commit; only later evidence/navigation documentation changes follow. New runtime files are the fixed packaged JSON catalogue and the fresh accessor module; the accepted inventory/binding/State/Capability validators are unchanged. No runtime dependency is added.

## Local Environments and Execution

Linux aarch64, non-root UID 1000; CPython 3.12.12 and 3.14.3, pytest 9.1.1. Tests use the explicit source path in `pytest.ini`; the import subprocess explicitly targets the same checkout, because the 3.14 environment contains an older installed package. The first 3.14 run had one import-probe failure from that older package; fixing the probe's source selection produced the final full success below. Installed-wheel tests use separate fresh environments and isolated import mode. No author Android/Termux or CPython 3.14.6 run is claimed for this implementation. No provider credentials, service, device or dispatcher.

```bash
/tmp/req014-env/bin/python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests \
  --require-inventory-runtime --require-binding-runtime --require-state-runtime \
  --require-capability-runtime --require-initial-capabilities-runtime -q \
  --junitxml=/tmp/req017-py312-results.xml
/tmp/req015-py314-env/bin/python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests \
  --require-inventory-runtime --require-binding-runtime --require-state-runtime \
  --require-capability-runtime --require-initial-capabilities-runtime -q \
  --junitxml=/tmp/req017-py314-results.xml
/tmp/req014-env/bin/ruff check libs/state-schema/src libs/state-schema/tests
/tmp/req014-env/bin/mypy --config-file libs/state-schema/pyproject.toml libs/state-schema/src
bash scripts/check.sh
python3 tools/check_home_intelligence_public_data.py
python3 tools/check_home_intelligence_requirements.py
git diff --check
```

Both interpreters: **1493 passed, zero skipped/failed**. Ruff 0.16.10 and strict mypy 2.4.0 (six source files) pass. All governance gates, 21 planning regressions, public-data/legacy requirements, targeted local links and whitespace checks pass.

| Scope | Passed per interpreter | Skipped | Failed |
|---|---:|---:|---:|
| TC-017-01 identity/schema/unit/exact selection | 44 | 0 | 0 |
| TC-017-02 canonical scalar boundary matrix | 71 | 0 | 0 |
| TC-017-03 action metadata and read-only selection | 35 | 0 | 0 |
| TC-017-04 fresh retrieval/resource faults/privacy | 20 | 0 | 0 |
| TC-017-05 actual State evidence boundary | 23 | 0 | 0 |
| TC-017-06 explicit read/import/acceptance gates | 4 | 0 | 0 |
| Existing inventory/binding/State/Capability/guards | 1296 | 0 | 0 |

197 new cases include 195 actual catalogue/validator/State/resource/import-boundary cases and two isolated real pytest acceptance probes. Resource fault injection replaces only package discovery/read; actual duplicate-key decoding and descriptor/catalogue validation run. Forbidden-effect guards record attempts and fail on swallowed effects. These exercise standard Python paths, not an OS/native-code sandbox. No provider execution is mocked into existence.

## Packaging and Installed-wheel Verification

After committing `c1901bf`, run:

```bash
uv build --offline --cache-dir /tmp/ai-family-uv-cache \
  --out-dir /tmp/req017-final-dist libs/state-schema
```

Wheel and sdist build successfully using cached hatchling dependencies. Archive inspection confirms exactly one `state_schema/initial_capabilities.v1.json` in the wheel and one `src/state_schema/initial_capabilities.v1.json` in the sdist, with identical parsed six-descriptor contents. The normal package inclusion configuration suffices; no source-tree-only resource fallback is used.

Install the final wheel offline with no dependencies into fresh `/tmp/req017-wheel312` and `/tmp/req017-wheel314`, then from `/tmp` execute each interpreter with `-I` against committed `libs/state-schema/tests/wheel_smoke.py`. Both pass. The smoke checks installed-module paths and calls the accessor to read all six descriptors, validate representative known readings, reject missing/invalid readings, unknown revisions, float/out-of-range opening, sensor actions and ACK-shaped outputs, and verify snapshot isolation. Existing State/Capability smoke still passes. No checkout import-path injection is used for these wheel runs.

CI requires all five runtime flags, lint/type, public-data/legacy checks and installed-wheel smoke on Python 3.12/3.13/3.14. CI results and final handoff are recorded after completion below.

## Review Limits

The accessor makes one explicit fixed package-local read per call; import does not read the catalogue. It performs no conversion, discovery, Device attachment, State update, task engine, provider execution, timer, retry or authorization. Generic REQ-016 validation still accepts structurally valid foreign definitions; the initial accessor additionally enforces its six ordered revision-1 pairs. Units/direction are defined by deliberately supported identity/revision/property meanings, not parsed from text.

Position type is enforced by the actual Capability property/input validator. REQ-015's generic scalar matching still permits numeric integer/float agreement; future integration must validate canonical observations before State updates. This slice supplies no such adapter/store integration or physical-device certification. Valid null action output/ACK creates no observation and never independently proves convergence. Human final approval of the specification does not accept this implementation.

## Implementation CI and Stop Boundary

[CI run 37889980293](https://github.com/rushwing/ai-family/actions/runs/37889980293), evidence head `f4f430c`, passes all eight applicable jobs: governance-gates, changes, req002-integration, goal-agent, mcp-toolsets and state-schema-tc on Python 3.12/3.13/3.14. Two unrelated web/workbook jobs skip by change detection. Each contract job runs lint/type, the five-flag required suite, public-data/legacy validation and installed-wheel smoke. Runtime/source/test artifact remains `c1901bf`.

T12 ends req_impl and hands off `req_impl_review` / evaluator-001 for the external combined review arranged by human-001. [PR #34](https://github.com/rushwing/ai-family/pull/34) stays draft. TC-017-01–06 stay implemented and AC1–AC7 unchecked. No independent approval, ready or merge is inferred from passing author/CI checks. Final handoff documentation has a separate CI run without runtime changes.

## Human-supplied Pre-reviews and Final Merge Disposition

[human-001][2026-10-09] Supplied the local and fresh-eyes non-signing pre-reviews of `2120ee10`, then explicitly requested merging PR #34 and done archival. The reviewer reports Android/Termux aarch64 / CPython 3.14.6 / pytest 9.1.1: 1493 passed, zero failed/skipped; per-TC 44/71/35/20/23/4, governance/21 planning regressions, public-data/legacy checks, wheel/sdist contents and isolated installed-wheel smoke passed. Both reports find no P0/P1/P2 defects. Adversarial probes confirm common resource failures, no import-time catalogue read, detached snapshots and actual absent/skip acceptance gates.

S-1 additionally demonstrates that structurally valid same-identity/revision content changes pass the accessor, while independently transcribed TCs detect schema/metadata drift. Retain the specified structural/pair guard and document this precise boundary, alongside the OSError/UnicodeError wrapper limit, synchronized identity/resource revisions and Capability-before-State integration obligation. This is an informational disposition, not a code defect or review return. Full dispositions are in the REQ; review_round remains 0 and runtime/source/test artifact remains `c1901bf`.

The supplied results apply to `2120ee10`, not the later documentation-only acceptance/closeout commits. They are reviewer-performed, not author Termux runs or independent T07/T10/T13 signatures. CI run 37890171479 verifies the same head with eight successes and two path-filtered skips. The report's baseline/mypy counts are corrected here to 1296 existing tests and six source files.

Human final acceptance accepts AC1–AC7 and TC-017-01–06 under the explicit merge/archive instruction. REQ-017 moves to pr_draft / human-001 pending authorized merge; TCs become passing. Historical pending-acceptance statements are superseded without inventing independent evaluator signatures.
