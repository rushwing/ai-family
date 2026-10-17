# REQ-028 / HI-S006 proposed normalization delivery

## Authority and scope

[human-001][2026-10-17] Instructed “Merge PR and start to implement, stop after
req_impl for external review.” PR #56 was exact-head squash-merged as
296237c3a2861a4439f5bfa9e12a49db098befbf; its accepted REQ-027 is archived.
The next eligible story HI-S006 is admitted to REQ-028. Generator-001 supplies
proposed specification, TC text/code and runtime for combined external review.
No independent evaluator signatures or new acceptance are supplied.

Source a49db405d7a4a3be5c5f64e1e7a0a0c00d461e4b implements a pure explicit
HA event adapter. Validated inventory/bindings and per-entity profiles determine
canonical identity and conversion; entity names never determine either.
Switch/curtain/Celsius deltas preserve false/zero, unknown/offline/history,
explicit UTC time and owner-supplied ordering. Returned records contain no HA
payload. State owners route deltas by canonical IDs and apply observed members,
retaining desired intent. Multi-entity device aggregation, source deduplication,
epoch allocation/persistence, store/reconciliation, live HA and writes are deferred.

## Executed verification

Linux aarch64 / CPython 3.12.12, against source-identical bytes at a49db40:

- Complete required fabric suite: **966 passed**, zero failures/errors/skips,
  with all nine runtime flags; shared suite: **1795 passed**, zero failures/skips.
- Normalization file: **86 cases**, including real subscription-client delivery
  through a fake transport into the normalizer. TC-028-01/02/03/04 marker groups:
  **19 / 59 / 6 / 9** (the last includes seven hermetic required-runtime probes).
- Exact canonical conversions, minimum Celsius boundary, missing position,
  malformed inputs, instance isolation, detached configuration, removal/unknown,
  replay/stale/conflict/epoch fencing and timestamp reversal are asserted.
- **Six source mutations detected**: false becomes true, position accepts bool,
  unit guard removed, ordering discarded, offline becomes online and unknown
  becomes false. Each isolated pytest subprocess exits 1 through real assertions;
  no timeout, signal or skip counts. Transformations, selections, source/log
  SHA256 and per-probe results are retained in provenance.
- Ruff and strict mypy (14 runtime sources), governance gates, **21 planning
  regressions**, nine-flag CI-wiring mutation checks, public-data and requirements
  checks pass. Secret scan includes all 817 tracked files; 25 changed REQ/TC
  Markdown local links resolve. git diff --check passes.

## Clean-source installed artifacts

Fresh complete builder retry records **source_dirty:false** at a49db40.
Both direct and sdist-derived shared/fabric wheel pairs build/install with all
**eight dependency wheels verified against official release metadata**. All
retained installed smokes pass. The four new normalization checks (both pairs
under -I and -O -I) each report five checks and offline:true; their explicit
conditional failures survive optimized Python. Source/artifact/dependency,
JUnit/per-TC and verification-source SHA256 are in the
[machine-readable provenance](REQ-028-artifact-provenance.json).

Initial fabric execution inside the sandbox could not bind required loopback
sockets; the complete outside-sandbox rerun above is authoritative. First local
builder metadata acquisition reset its connection after download; that incomplete
attempt is not acceptance evidence. The fresh retry completed independently.
No local Python 3.13/3.14, Windows/Termux, private HA or hardware result is inferred.
CI separately runs the declared three-version package matrix; final-head status
is maintained in [draft PR #57](https://github.com/rushwing/ai-family/pull/57).

## External review stop

Remain req_impl / generator-001, review_round 0, AC1–AC4 unchecked and
TC-028-01–04 implemented. Evidence/link follow-up changes no tested runtime,
test, smoke or CI bytes. PR #57 stays draft. External review, human acceptance,
merge, BUG-033 and Feature/Stage completion retain separate gates.
