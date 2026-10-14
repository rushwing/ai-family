# REQ-024 — PR #51 merge and done ledger

Date: 2026-10-15. [human-001] supplied the third-pass re-review of head 5cd68ad
and explicitly instructed: “Merge the PR and then do the ledger and housekeeping
in another PR”. This accepts AC1–AC8 and the combined TC-024-01–06 text/code/
runtime delivery, including both recorded review-fix rounds. It supersedes the
historical req_impl/draft/unmerged stop. Human final acceptance is the authority;
no registered evaluator identity, independent T03/T07/T10/T13 signature or full
independent artifact-builder execution is invented.

## Merge provenance

[PR #51](https://github.com/rushwing/ai-family/pull/51) was marked ready under
that instruction and squash-merged with exact-head matching on
`5cd68ad52569261577d24a1a1c0fc4883f9f5954` at 2026-10-14T22:58:58Z
(2026-10-15 06:58:58 Asia/Shanghai), as
`2d986a784a7784f496779d50c6eec6365518eeae`. GitHub state/merge metadata was
read afterward; local main was fast-forwarded before creating the separate
codex/req024-closeout branch.

[Final-head CI run 38644024265](https://github.com/rushwing/ai-family/actions/runs/38644024265)
passes all 11 applicable jobs, including shared/fabric matrices on Python
3.12/3.13/3.14, required tests and installed artifact verification. Two unrelated
product jobs are path-filtered. The runtime/test diagnostic-fix source is
`a006c9753c8a09c75b7c457a5bbab182f208b01a`; final head 5cd68ad adds delivery
metadata. The source [CI job](https://github.com/rushwing/ai-family/actions/runs/38643556484/job/116124836572)
reports 697 required fabric passes. [Residual disposition](REQ-024-rereview-fixes.md)
records 93 unoptimized local Linux lifecycle/gate passes and 55 targeted Windows
passes. These counts are source-specific execution evidence, not a newly
reproduced full post-merge matrix.

## Review attribution and limits

The user supplied three attributed review reports. The third reports independent
55 WebSocket and 38 gate passes, lint/type/CI-wiring passes, matching -I/-O -I
smoke output, and 694 Windows fabric passes plus three pre-existing failures.
The preceding review reports the fourth shared-suite os.geteuid failure and
base f2e201b reproduction. These are reviewer-supplied observations, not this
session's new base-reproduction execution or registered Harness signatures.
The reviewer explicitly did not execute the full artifact builder end to end.
The actual local paired-build records remain in the initial/review provenance
JSON, and the CI matrix supplies its own installed-pair execution. Neither is
retroactively labeled an independent artifact-builder run.

Historical provenance JSON is preserved. [BUG-032](../bugs/BUG-032.md) remains
open for the REQ-023 dependency-identity discrepancy, with original wheel bytes
and cause unverified. [BUG-033](../bugs/BUG-033.md) separately records the four
pre-existing Windows portability failures. Neither is an unresolved req_bug
linked to REQ-024. No live HA, private household credential or physical-device
certification is claimed. Unoptimized pytest is acceptance evidence; only
explicit-require() installed smoke programs supply -O -I optimization coverage.

## Post-merge verification

Merged source 2d986a7, WSL Linux x86_64 / CPython 3.12.12, existing compatible
editable distributions in /home/cloudbokeh/.cache/ai-family-req024-env:

```bash
python -I toolsets/iot/home-device-fabric/tests/ha_websocket_artifact_smoke.py
python -O -I toolsets/iot/home-device-fabric/tests/ha_websocket_artifact_smoke.py
```

Both pass with identical JSON: authenticated shutdown, terminal auth rejection,
finite reconnect and preserved closed reasons; four wire auth exchanges per run,
websockets 15.0.1, certifi 2026.7.22 and the actual CA bundle hash. This post-merge
editable-environment smoke is separate from fresh installed-wheel verification;
no new wheel hashes, full matrix or live installation is claimed.

## Harness and navigation

T15: [REQ-024](../archive/done/features/REQ-024.md) is done / human-001,
review_round 0, pr_number 51, eight human-accepted ACs and six passing TCs.
TC owner remains generator-001, reflecting actual proposed test authorship.
No pending or linked unresolved req_bug blocks done. Earlier pending-review
statements remain historical and are superseded by this explicit acceptance.

Archive the sole authoritative REQ, rebase its relative links, repair TC/evidence/
product navigation, refresh HI-S003 delivery guidance and keep intentional
planning mutation fixtures active. index.json already resolves HI-S003 to
REQ-024 and derives engineering state from Harness; no duplicate lifecycle is
added. Bounded WebSocket lifecycle delivery does not complete subscriptions,
combined integration health, physical-device acceptance, HI-F001 or R1.

This separately requested housekeeping PR changes ledger/documentation and the
planning fixture only. Production runtime, runtime acceptance test code, CI and
historical artifact-provenance JSON stay unchanged from merged main. The
housekeeping PR remains unmerged for user review.

## Closeout validation

All nine local governance checks pass: ADR, layout, agent registry, secrets,
RLS, Home Intelligence planning/public data/requirements, and fabric CI wiring.
The Linux planning regression suite passes 21 tests after including the new
acceptance and BUG-033 records in its isolated fixture. Relative links in all
changed/new Markdown resolve; the sole archived REQ has eight checked ACs and
all six TCs are passing. The runtime/CI/provenance scope guard and git diff
whitespace check pass. Post-merge smoke JSON is byte-identical in both modes;
CA bundle SHA-256 is
`9cc2a774b5198dcff14d9be1e66091f538975d867ce029a96bce15a55dfd730f`.
