# REQ-024 residual re-review disposition

**Known Windows limitation:** the reviewed CPython 3.13.2 environment has four
pre-existing full-suite failures: three REST timing/socket tests and the
inventory os.geteuid test. The supplied re-review reproduced them at base
f2e201b. Targeted Windows passes do not certify full Windows acceptance.

**Optimization scope:** pytest acceptance counts use unoptimized interpreters.
Running pytest with python -O is not acceptance evidence because assertions
are stripped. Only installed explicit-require() smoke programs provide -O -I
coverage; those are a separate verification path.

## Authority

On 2026-10-15 human-001 supplied the re-review of PR #51 head 26dec5b and
instructed “Fix all findings”. The supplied report attributes its new executions
and base reproduction to its author. It still supplies no registered Harness
reviewer signature or authority to merge/advance. This session acts as
generator-001 within req_impl. The eight ACs remain unchecked, six TCs remain
implemented, and PR #51 remains draft and unmerged.

## Residual findings

| Item | Fix |
|---|---|
| 1: meaning of reason on closed | Public health/close docstrings, the normative REQ and README explicitly say it is the last observed lifecycle cause, not a close failure. Clean post-exhaustion close retains reconnect_exhausted. Existing behavior and wire/installed assertions remain unchanged. |
| 2: swallowed drain failures | The closer docstring and REQ/README explicitly document deliberate worker/drain-failure consumption. The worker owns guarded finally cleanup/abort; run is the worker-error reporting path. Close is not a cleanup-result API. No error-handling policy is silently changed. |
| 3: broken versus absent imports | ImportError produces finite absent diagnostics; other ordinary import failures produce broken diagnostics. Required mode still exits 4 and optional mode still skips, but both now distinguish the two cases without exception text. Real-hook tests assert those messages for RuntimeError and AttributeError, including optional skip summaries. |
| 4: pytest -O evidence | Prominent evidence/README notes distinguish unoptimized pytest from explicit-require() installed -I/-O -I smoke. No optimized pytest count is claimed as behavioral proof. |
| 5: Windows attribution | Both prior human-readable evidence documents and the module README now flag the known full-Windows failures near their relevant top. The re-reviewer's base reproduction is attributed; no full Windows pass is claimed. |

## Scope and remaining historical issue

Runtime changes are docstrings only. Test-hook diagnostics and corresponding
real-hook regressions change; full-suite acceptance and installed smokes remain
required in the CI matrix. The previous static-review fixes and provenance are
historical records of their stated sources, not evidence for this new source.
BUG-032 remains open for historical REQ-023 dependency-byte identity; the new
re-review supplies no original wheelhouse or root cause. Previous provenance
JSON records remain unchanged.

## Local verification

- Linux CPython 3.12.12: unoptimized WebSocket and real-hook gate regression
  run passes 93 tests with zero failures/errors/skips. TC-024-06 includes the
  two new AttributeError rows and explicit required/optional message checks.
- Windows CPython 3.13.2: unoptimized targeted WebSocket run passes all 55 tests.
- Ruff and strict mypy pass; planning navigation validation passes.
- The installed smoke source is unchanged. CI retains both direct/sdist-derived
  package pairs under -I and -O -I; optimized pytest is not used as proof.

Commands: python -m pytest -c toolsets/iot/home-device-fabric/pytest.ini followed
by tests/test_ha_websocket.py and tests/test_gate.py from that module, with
--require-ha-websocket-runtime -q --tb=short (Linux); Windows runs the WebSocket
file with the same interpreter flags. No Python -O flag is present in either
pytest run. Historical full-Windows limitations remain as stated at the top.

## Verified source and CI delivery

Diagnostic/test and docstring source is
`a006c9753c8a09c75b7c457a5bbab182f208b01a`. Subsequent delivery metadata is
documentation only. [CI run 38643556484](https://github.com/rushwing/ai-family/actions/runs/38643556484)
passes all 11 applicable jobs, with two unrelated path-filtered skips. Both
shared/fabric matrices pass on Python 3.12/3.13/3.14, including installed artifact
verification. The [Python 3.12 fabric job](https://github.com/rushwing/ai-family/actions/runs/38643556484/job/116124836572)
reports **697 passed**, with all six required-runtime flags and no required
skips/failures/errors. The same job separately passes all four installed
REQ-024 lifecycle smoke executions across direct/sdist-derived pairs and
-I/-O -I, using explicit require() checks. The 697 pytest count is unoptimized;
it is not an optimized-pytest claim.

No acceptance, merge or lifecycle advancement is inferred from the re-review
or these checks. Remain req_impl / generator-001, eight unchecked ACs, six
implemented TCs, draft and unmerged pending external review. BUG-032 remains
the separate historical-evidence follow-up; its original records are unchanged.
