# REQ-013 TC implementation self-check

Tested code commit: `03d088723e37f828ec00a63384c45e806789c9cf` (clean working tree).
Date: 2026-10-08. Environment: Linux, Python 3.13.5, pytest 9.1.1,
Ruff 0.16.10, isolated uv tool environments with cache under `/tmp`.
The runtime package and its validation dependency do not exist yet; no HA
endpoint, device or credentials were used. CI runs with Python 3.12 and uploads
its own JUnit results as `req013-tc-results`.

Commands run from the repository root:

```bash
uvx --offline --cache-dir /tmp/ai-family-uv-cache pytest -c libs/state-schema/pytest.ini libs/state-schema/tests -q --junitxml=/tmp/req013-results.xml
uvx --offline --cache-dir /tmp/ai-family-uv-cache pytest -c libs/state-schema/pytest.ini libs/state-schema/tests --require-inventory-runtime -q
uvx --offline --cache-dir /tmp/ai-family-uv-cache ruff check libs/state-schema/tests
bash scripts/check.sh
python3 tools/check_home_intelligence_public_data.py
```

| Scope | Passed | Skipped | Failed |
|---|---:|---:|---:|
| TC-013-01 | 0 | 38 | 0 |
| TC-013-02 | 0 | 11 | 0 |
| TC-013-03 | 0 | 329 | 0 |
| TC-013-04 | 0 | 3 | 0 |
| TC-013-05 | 0 | 13 | 0 |
| TC-013-06 | 0 | 57 | 0 |
| TC-013-07 | 0 | 8 | 0 |
| Infrastructure guards (not runtime acceptance) | 7 | 0 | 0 |

Ordinary TC run: exit 0, **7 infrastructure checks passed / 459 runtime cases
skipped / 0 failures**, 466 collected. Every runtime skip reports:
`REQ-013 runtime state_schema.home_inventory is not implemented; acceptance pending`.
The table is derived from the local JUnit report, not inferred from test names.
The local report is ephemeral; repeat the recorded command or inspect the CI
artifact for case-level output.

Acceptance-mode negative check: exit **4**, with
`ERROR: REQ-013 inventory runtime is missing; acceptance cannot pass`.
This confirms that missing runtime code cannot yield successful acceptance.

Ruff passed; governance passed, including all 21 planning/admission regressions;
public-data and staged secret scans passed. Whitespace and changed Markdown
local links passed. No package type checker is configured in this test-only
placeholder; selecting the runtime validation library and its applicable type
checks remains implementation work.

All seven TCs are `implemented`, never `passing`. TC-code independent review is
pending; runtime acceptance still requires executing the actual package,
resolving every skip and replacing this test-first evidence with implementation
commit/environment results. The test seam and instrumentation limits are
recorded in the [suite instructions](../../../libs/state-schema/tests/README.md).
