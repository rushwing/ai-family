# REQ-013 combined review and acceptance

Date: 2026-10-08. PR: [#26](https://github.com/rushwing/ai-family/pull/26).
Reviewed implementation: `124b9ec`, recorded at `96e3ce8`.
Tested polish commit: [b611697](https://github.com/rushwing/ai-family/commit/b611697).
Environment: Linux, Python 3.13.5, pytest 9.1.1, Ruff 0.16.10, mypy 2.4.0.

## Independent review supplied by human-001

Human-001 reported the completed independent ChatGPT review: no blocking
findings. It confirms strict offline validation, provider-free canonical
records, deterministic/fail-closed resolution and no action-dispatch path.
The combined TCs meaningfully cover malformed inputs, duplicate JSON fields,
selector ambiguity, empty selections, private-copy workflow and offline CLI
guards. Reviewer locally passed governance/planning (21 regressions), Python
compilation, fixture loading and resolver smoke: Resting + children selects
only Daughter's Room/light; empty selectors fail correctly.

The single non-blocking request was to preserve structured error paths while
rendering loader errors as `file: $.field: reason` exactly once. Human-001
explicitly authorized fixing it and merging PR #26. This records that supplied
independent review rather than claiming a new independent review by the author.

## Correction and verification

`InventoryError` retains the raw reason separately from its formatted string.
The loader supplies filename context when formatting the error, preserves
`error.path` and chains the underlying exception. Direct validation/resolver
errors retain their existing formatting. CLI failures still return exit code 2
and emit no inventory output.

TC-013-07 now checks filename-first formatting and a single JSON path across
malformed JSON, unsupported versions, invalid fields/references, file/encoding
failures, duplicate fields and nonstandard constants. Two new exact-output API
and CLI cases verify root-field and nested-array paths, reasons and exception
chaining under the existing offline guards.

```bash
uvx --offline --cache-dir /tmp/ai-family-uv-cache pytest -c libs/state-schema/pytest.ini libs/state-schema/tests --require-inventory-runtime -q --junitxml=/tmp/req013-polish-results.xml
uvx --offline --cache-dir /tmp/ai-family-uv-cache ruff check libs/state-schema/src libs/state-schema/tests
uvx --offline --cache-dir /tmp/ai-family-uv-cache mypy --config-file libs/state-schema/pyproject.toml libs/state-schema/src
bash scripts/check.sh
python3 tools/check_home_intelligence_public_data.py
git diff --check
```

| Scope | Passed | Skipped | Failed |
|---|---:|---:|---:|
| TC-013-01 | 39 | 0 | 0 |
| TC-013-02 | 11 | 0 | 0 |
| TC-013-03 | 329 | 0 | 0 |
| TC-013-04 | 3 | 0 | 0 |
| TC-013-05 | 13 | 0 | 0 |
| TC-013-06 | 57 | 0 | 0 |
| TC-013-07 | 16 | 0 | 0 |
| Infrastructure guards | 7 | 0 | 0 |

**475 passed, 0 skipped, 0 failed**, including 468 runtime cases. Ruff and strict
mypy pass. Governance, all 21 planning regressions, public-data/secret scans and
whitespace pass. Historical wheel/build and Python 3.12 CI evidence is retained
in [runtime evidence](REQ-013-runtime-implementation.md).

Planning regression fixtures now accept the live REQ from its active or archived
location while keeping mutation fixtures active; this permits normal post-merge
archival without coupling tests to the live lifecycle.

## Harness disposition

Record deferred T10 from the supplied independent combined review. After the
bounded polish and successful gates, record T12 and T13, accept AC1–AC7 and mark
TC-013-01–07 passing. REQ-013 advances to `pr_draft` / human-001; PR readiness
follows this recorded review. `pending_bugs` is empty and no BUG links REQ-013.
Human-001 authorized T15 merge after final-head CI. Engineering completion and
archival are recorded only after GitHub confirms merge.
