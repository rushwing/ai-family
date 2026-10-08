# REQ-013 runtime implementation evidence

Tested feature commit: `124b9ec3c55f20b8414ae176c6bf8601fee7554d` (clean working tree).
Date: 2026-10-08. Local environment: Linux, Python 3.13.5, pytest 9.1.1,
Ruff 0.16.10 and mypy 2.4.0. Runtime dependencies: none. Package version:
`ai-family-state-schema==0.1.0`. Only fictional inventory files were used.

The human authorized proceeding with feature implementation before a separate
TC-code review and will arrange ChatGPT review of the combined result. These
are Generator self-check results, not T10/T13 approval. REQ acceptance boxes
remain unchecked, and no `done` or independent acceptance is claimed.

## Runtime results

```bash
uvx --offline --cache-dir /tmp/ai-family-uv-cache pytest -c libs/state-schema/pytest.ini libs/state-schema/tests --require-inventory-runtime -q --junitxml=/tmp/req013-runtime-results.xml
uvx --offline --cache-dir /tmp/ai-family-uv-cache ruff check libs/state-schema/src libs/state-schema/tests
uvx --offline --cache-dir /tmp/ai-family-uv-cache mypy --config-file libs/state-schema/pyproject.toml libs/state-schema/src
bash scripts/check.sh
python3 tools/check_home_intelligence_public_data.py
```

| Scope | Passed | Skipped | Failed |
|---|---:|---:|---:|
| TC-013-01 | 39 | 0 | 0 |
| TC-013-02 | 11 | 0 | 0 |
| TC-013-03 | 329 | 0 | 0 |
| TC-013-04 | 3 | 0 | 0 |
| TC-013-05 | 13 | 0 | 0 |
| TC-013-06 | 57 | 0 | 0 |
| TC-013-07 | 14 | 0 | 0 |
| Infrastructure guards | 7 | 0 | 0 |

**473 passed, 0 skipped, 0 failed**: 466 runtime TC cases and 7 guard checks.
The counts come from the JUnit report, not estimates. All original 459 runtime
cases now execute; added cases cover frozen domain identity/detached snapshots,
duplicate JSON fields and nonstandard numeric constants. The unreadable-file
case ran successfully as an unprivileged user.

The actual CLI ran in subprocesses with audit instrumentation denying network,
child-process and filesystem-write attempts, including swallowed attempts.
The resolver's direct calls also ran under socket/process/write guards and
input snapshots. No provider/action entry point was introduced in the runtime.

Ruff and strict mypy passed (2 source files). Governance passed, including all
21 planning/admission regressions. Public-data/secret scans, whitespace and
changed Markdown local-link checks passed.

## Distribution verification

```bash
uv build --offline --cache-dir /tmp/ai-family-uv-cache --out-dir /tmp/req013-dist libs/state-schema
uv venv --python /usr/bin/python3 /tmp/req013-runtime-env
uv pip install --offline --cache-dir /tmp/ai-family-uv-cache --reinstall --python /tmp/req013-runtime-env/bin/python /tmp/req013-dist/ai_family_state_schema-0.1.0-py3-none-any.whl
```

Both source distribution and wheel built. From `/tmp`, the installed wheel's
Python interpreter imported the runtime from its own environment (verified
module location), loaded the public fixture, resolved Resting + children to
exactly `area-bedroom-02` / `device-bedroom-light-02`, ran the real CLI and
compared its parsed JSON to the loader output. The distributed `py.typed` marker
was also verified. These smoke checks passed with the final code commit's wheel.

The local JUnit report and distributions are ephemeral `/tmp` artifacts. [CI run 37754018357](https://github.com/rushwing/ai-family/actions/runs/37754018357)
passed all applicable checks at the tested feature commit, including required
runtime tests on Python 3.12, and stores case-level JUnit output in `req013-tc-results`; it now
requires acceptance mode with no skips, package installation, Ruff and mypy.
Independent combined TC-code/feature review is still required.

## Review entry points

- [Requirement and acceptance](../archive/done/features/REQ-013.md)
- [Runtime contracts, loader and resolver](../../../libs/state-schema/src/state_schema/home_inventory.py)
- [Package/API design and commands](../../../libs/state-schema/README.md)
- [Test assertions and guard limits](../../../libs/state-schema/tests/README.md)
- [Apartment/private-copy instructions](../../../docs/product/home-intelligence/examples/README.md)
- [Earlier test-first evidence](REQ-013-tc-implementation.md)

Review should cover the standard-library validation design, error paths,
immutable identity and detached snapshots, cross-home/reference rejection,
selector unions/intersections, lack of fallback/provider actions and the actual
assertions/guard coverage. Direct dataclass constructors are typed internal
records; external data must enter through `from_dict` or the JSON-facing APIs.
