# REQ-023 — F10 BaseException cleanup follow-up

[human-001][2026-10-14] Supplied the expanded local pre-review and instructed
“Fix all new findings”. This is expressly not an independent review signature.
The report's repeated F0–F9 assertions describe b427167b. GitHub was checked
before this follow-up: the actual head was ecd49fff243ec3901b6aab52f1aba2c8f289eec3,
open/draft, with no reviews or comments; the prior fixes are present.

## New finding and change

F10 also applies to ecd49ff: exceptions outside Exception, including
KeyboardInterrupt/SystemExit/GeneratorExit, escape read processing before the
operation cleanup is reached. Send failures leave the transport unclosed; body
failures leave response and transport unclosed.

Runtime/test source
`371fc0b08b7cfe6f88bd77ba8dee380e80b8fd4f` moves the existing aggregate bounded,
cancellation-safe cleanup into the read try's finally. Ordinary classifications,
post-cleanup deadline priority and cancellation handling retain their contracts.
Process-control exceptions propagate unchanged after attempted owned closure;
ordinary close exceptions or guard expiry do not replace them. The outer finally
still clears admission and signals completion, allowing later calls and draining
close to finish. No new independent approval or lifecycle transition is inferred.

TC-023-04 adds 18 cases: three exception types × send/body stages × normal close,
ordinary close exception or cleanup guard expiry. Each case catches the original
exception inside the caller coroutine, checks its identity, counts all owned
close attempts, then demonstrates subsequent admission recovery and explicit
close. This avoids asyncio's special treatment of uncaught KeyboardInterrupt and
SystemExit crossing a Task boundary masking the resource assertions. Restoring
the pre-fix runtime in an isolated copy makes all 18 cases fail. The previous
28 targeted mutations also remain detected by their regressions.

This covers cleanup attempted during coroutine unwinding, not externally killed
processes, interpreter shutdown or synchronous dependency code that cannot yield.
A close attempt is not a claim of resource release when that close itself fails
or exceeds its guard. Existing private-inspection/traceback-frame exclusions
continue to apply; ordinary HARestError diagnostics remain value-free.

## Validation

The [current provenance](REQ-023-f10-provenance.json) records the tested runtime
commit, interpreter/tool versions, source and per-TC counts, isolated mutation
results and complete rebuilt artifact/dependency reports. Prior
[fix evidence](REQ-023-pre-review-fixes.md) and
[provenance](REQ-023-fix-provenance.json) remain historical evidence.

Remain req_impl / generator-001, eight ACs unchecked, TC-023-01–06 implemented,
and PR #49 draft and unmerged. F5's explicit acceptance of post-cleanup deadline
priority, independently derived external T07/T10 expectations and human-governed
T12/T13/readiness/merge remain pending; no signatures are fabricated.


Executed on Linux aarch64, CPython 3.12.12 / 3.13.5 / 3.14.3: each passed
630 fabric and 1795 shared tests with zero failures/errors/skips. Per-TC counts
are 5 / 56 / 61 / 35 / 5 / 6, totaling 168 REQ-023 cases (162 REST and six gate
probes) above the unchanged 462-test baseline. Ruff 0.17.0 and strict mypy 2.4.0
passed on every interpreter. Six rebuilt direct/sdist-derived package pairs
passed twelve installed REST smokes under -I / -O -I and the existing
provider/demo/conformance/configuration smokes. All reported artifact/dependency
hashes were recomputed; installed REST module hashes match the revised source.

Governance gates, 21 planning regressions, legacy requirements/public-data checks,
local Markdown targets and git diff --check pass. Published-head CI is checked
separately. The only new implementation finding, F10, is repaired; F0–F9 retain
the prior dispositions, with independent approval/process decisions pending.
