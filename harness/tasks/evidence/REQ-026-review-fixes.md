# REQ-026 local pre-review remediation

[generator-001][2026-10-16] Addresses the user's non-signing PR #54 local
pre-review. Tested implementation/test/CI source:
`a068330ca58d0c4fe8b5ee871a973861c2a20c27`.
This record supplements the [initial delivery](REQ-026-runtime-implementation.md);
its historical provenance remains unchanged.

## Findings and changes

- F1: All asynchronous fake-peer scenarios now have a three-second deadline,
  release cancellation gates, advance fake time and drain remaining tasks on
  failure. The gated late-result regression additionally requires run completion
  within 200 scheduler yields without advancing fake time. Deleting the probe's
  closed guard fails both parameter cases by assertion in 0.21 seconds, rather
  than hanging or reaching either deadline.
- F2: Isolated tests exercise the publisher directly after closure, and replace
  publication with a recorder to exercise the sampler's independent guard.
  Deleting either guard now fails its own regression. Source and README explain
  the three guards as defense in depth, including protection of internal
  diagnostics and prevention of late interval scheduling.
- F3: A running health read without a running loop now raises exactly
  `RuntimeError("wrong_event_loop")`, with no stdlib exception context. A worker
  thread tests both synchronous/no-loop and foreign-loop reads before mutation.
  Initial and closed snapshots remain readable synchronously.
- F4: The reviewer's Termux ensurepip limitation requires no runtime change.
  No Termux/Windows/live HA execution is inferred. This local Linux builder
  attempt was interrupted during direct PyPI release-metadata socket connect;
  it did not complete and is not counted as a fresh-venv pass. CI supplies the
  complete installation verification below.

## Verification

Local Linux aarch64 / CPython 3.12.12:

- Required fabric: **797 passed**, zero failures/errors/skips, including **60**
  health tests. TC-026-01/02/03/04/05: **38 / 7 / 5 / 10 / 8**, overlapping.
  CI's explicit baseline is updated to 797.
- Required shared: **1795 passed**, zero failures/errors/skips.
- Nine isolated in-memory source mutations all fail actual named pytest
  regressions with exit 1: the original five plus publisher, sampler and probe
  closed guards and the no-loop error normalization. None reaches its 15-second
  outer timeout; probe deletion fails the finite settle assertion, not the
  scenario deadline. Machine evidence includes exact replacements and log hashes.
- Governance, all seven required CI flags, 21 planning tests, Ruff, strict mypy,
  public-data and legacy requirements checks pass.

[CI run 38861623356](https://github.com/rushwing/ai-family/actions/runs/38861623356)
for head `a068330` passes all 11 applicable jobs; two unrelated jobs are filtered.
Downloaded Python 3.12/3.13/3.14 provenance reports each record a clean synthetic
merge checkout `21412a260a8a66cde8eac3622a91731dde6ef3d0`; its parents were verified
as main `4447027` and the exact remediation head `a068330`. Each matrix leg
records 797 required fabric passes, eight verified official dependency wheels,
direct and sdist-derived distributions installed in fresh venvs, retained smokes,
and both health modes (`-I`, `-O -I`) for both pairs.

All six downloaded fabric wheels were independently opened: their health module
payloads match the local source SHA256
`bfa0cdb9816508f79ddd8b3edb3efeaf8949ffe06e6f5dd129c115f0672da4ce`.
All twelve installed health reports contain the nine expected checks.
[Remediation provenance](REQ-026-review-fixes-provenance.json) retains local
JUnit summaries/hashes, exact mutations, interrupted-builder status, CI report
hashes, dependency and artifact identities, health reports and payload hashes.

The original 13 pre-REQ-026 provenance JSON files and the accepted configuration,
REST, WebSocket and package initializer remain byte-identical to main. The
initial REQ-026 provenance is also unchanged. Subsequent remediation evidence
commits only document this tested source.

## Review boundary

This is generator remediation, with no independent T03/T07/T10/T13 signature.
REQ-026 remains req_impl / generator-001, review_round 0, five unchecked ACs and
five implemented TCs. PR #54 stays draft and unmerged. REQ-025's accepted archive
and BUG-033's separate scope are unchanged.
