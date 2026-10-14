# REQ-023 — PR #49 Merge and Done Ledger

Date: 2026-10-14. [human-001] explicitly instructed: “PR is OK to merge. And then do the ledger and house keeping in another PR”. This accepts AC1–AC8 and the combined TC-023-01–06 text/code/runtime delivery, including recorded F0–F10 fixes and post-cleanup deadline priority, and supersedes the earlier req_impl/draft/unmerged stop. The instruction supplies human final acceptance; no separate external report, independent evaluator identity, T03/T07/T10/T13 signature, bot approval or independent matrix reproduction is invented.

## Merge Provenance

[PR #49](https://github.com/rushwing/ai-family/pull/49) merged at 2026-10-14T09:36:35Z. Final head: 404d1ac79acbb39bab1bf0d3563b39179dab36e1; squash: bbe348f1791ca83afb8c79a711b2e5c909bd8d39. Marked ready under explicit human authority and squash-merged using exact-head matching; GitHub state/merge provenance was read afterward. [Final-head CI run 38537891034](https://github.com/rushwing/ai-family/actions/runs/38537891034) passed all 11 applicable checks, including six fabric/shared Python 3.12/3.13/3.14 jobs; two unrelated product jobs were path-filtered. Local main was fast-forwarded before creating the separate housekeeping branch.

[Original delivery](REQ-023-runtime-implementation.md), [API contract](REQ-023-api-contract.md), [F0–F9 disposition](REQ-023-pre-review-fixes.md) and [F10 disposition](REQ-023-f10-fixes.md) preserve actual authorship and historical validation. [Current provenance](REQ-023-f10-provenance.json) identifies runtime/test source 371fc0b08b7cfe6f88bd77ba8dee380e80b8fd4f, resolved dependencies, mutation results and rebuilt artifacts; earlier provenance remains historical. Final PR head 404d1ac adds documentation/evidence after that runtime revision.

Historical Linux aarch64 matrix: Python 3.12.12 / 3.13.5 / 3.14.3 each passed 630 fabric and 1795 shared tests, zero failures/errors/skips; TC counts 5/56/61/35/5/6. Six direct/sdist-derived compatible wheel pairs passed twelve installed REST smokes under -I/-O -I and existing smokes; Ruff/strict mypy passed on every interpreter. Eighteen F10 regressions fail against the pre-fix runtime and all 28 earlier targeted mutations remain detected. These are recorded author-run results, not newly executed post-merge matrices or independent review evidence.

## Post-merge Verification

Source bbe348f1791ca83afb8c79a711b2e5c909bd8d39, Linux aarch64 / CPython 3.12.12, compatible editable distributions in /tmp/req019-env:

```bash
/tmp/req019-env/bin/python -I toolsets/iot/home-device-fabric/tests/ha_rest_artifact_smoke.py
/tmp/req019-env/bin/python -O -I toolsets/iot/home-device-fabric/tests/ha_rest_artifact_smoke.py
```

Both passed: wire=true, timeout=true, tls_verification=true, draining_close=true; HTTPX 0.28.1, optimized=false/true. Imported runtime SHA256: 3f2c44dbf25e7a634214599f1053f838812699a64167e13a441e1737bee98c83. The sandbox initially denied loopback sockets; execution with approved socket access passed. This editable-environment smoke is separate from historical fresh-wheel/outside-checkout builds. No new wheel hashes, full matrix or live HA run is claimed.

## Harness and Navigation

T15: [REQ-023](../archive/done/features/REQ-023.md) is done / human-001, review_round 0, pr_number 49, eight human-accepted ACs and six passing TCs. No pending or linked unresolved req_bug blocks done. TC owner remains actual proposed-text designer generator-001; automated code authorship and human acceptance are separately recorded.

Archive the sole authoritative REQ, rebase its links, repair TC/API/evidence/product navigation, refresh HI-S002 delivery/current-state guidance and retain deliberate active planning mutation fixtures. index.json already has reciprocal HI-S002/REQ-023 identity and derives engineering lifecycle from Harness, so needs no duplicated state. This closes the bounded read-only HI-S002 increment; live HA certification, WebSocket transport, HI-F001 and R1 remain separate. Historical stop/pending statements in delivery records are superseded by this human acceptance, not rewritten as prior approval.

The separate housekeeping PR changes documentation and planning-fixture maintenance only; production runtime, runtime acceptance tests, CI and artifact-provenance JSON remain unchanged from merged main.

Local closeout validation: governance gates (ADR, layout, agent registry, secrets, RLS), planning integrity and all 21 planning regressions, legacy requirements/public-data checks, all 111 local Markdown targets in changed/new documents and git diff --check passed. Verified the sole archived identity, eight accepted ACs, six passing TC records and unchanged actual designer ownership. Planning resolves HI-S002 → REQ-023 done / human-001. Published-head CI is checked separately.
