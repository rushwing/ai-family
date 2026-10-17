# REQ-028 local pre-review follow-up

The human supplied a non-signing local pre-review of PR #57 head 06dc896 and
instructed “Fix all findings”. This authorizes the generator follow-up, not
T03/T07/T10/T13 approval, requirement acceptance or merge. Source commit
55b8270ea5053d171b6e19f043e3c0e42f18c2f1 closes the three observations.

## Changes

- O1: REQ-028, TC-028-02 and package README explicitly require object attributes
  for every non-null new_state, including unknown/unavailable. Six cases cover
  missing/null/list attributes in both states, fixed error path and no mutation.
  Removal remains exempt. Installed smoke checks both missing-attribute cases.
- O2: The existing numeric-offset range is explicitly -23:59 through +23:59.
  This is an adapter duration contract, not a whitelist of civil time zones.
  Both signs of 14:01 and 23:59 have exact UTC expectations, and both signs of
  24:00 are rejected. Installed smoke checks both accepted 23:59 boundaries.
- O3: Canonical DeviceState StateError is mapped to HANormalizationError with
  code invalid_observation, fixed path ("observation",) and suppressed context.
  Fault injection verifies that private canonical keys/messages cannot appear
  in the public error or rendered traceback and input stays unchanged.
  The same error boundary is exercised by the installed smoke.
- O4: The reviewer's Termux ensurepip restriction remains an explicit validation
  limit. This Linux execution and CI package checks provide separate evidence;
  no new Termux fresh-venv claim is made.

## Actual verification

Linux aarch64 / CPython 3.12.12: **978 required fabric + 1795 shared passed**,
zero failures/errors/skips. Normalization: **98 cases**; TC-028 marker groups
**19 / 71 / 6 / 10** (overlap). All nine required runtime flags were supplied.
The first fabric execution caught the stale smoke-count expectation (5 instead
of 8); it is superseded by the completed clean-source rerun above.
Ruff, strict mypy (14 source files), governance including **21 planning tests**,
nine-flag CI wiring, public-data/requirements validation and whitespace pass.
Actual import-blocker probes preserve optional skipping (98 cases), required
absent/broken exit 4 and private-detail redaction; optional probe skips are not
part of the required-suite results.

Fresh clean-source builder records source_dirty:false. Both direct and
sdist-derived shared/fabric package pairs build and install; eight dependency
wheels are checked against official metadata. All retained installed checks
pass; the updated normalization smoke reports **8 checks, offline:true** in
all four runs under -I / -O -I. Artifact/source/dependency/test hashes are in
[follow-up provenance](REQ-028-review-fixes-provenance.json).

Five targeted mutations are detected by assertions: attributes bypass, invalid
offset minutes, accepted offset range narrowed, canonical error exposed, and
canonical exception context exposed. Each exits pytest 1 without timeout.
A sixth probe loosening only the hour guard from 23 to 24 survives because
CPython datetime still rejects 24-hour offsets; this redundant-guard survivor
is retained separately in provenance and is not counted as a killed mutation.

Historical evidence JSON and accepted HA modules remain unchanged. REQ-028
stays req_impl / generator-001, review_round 0, AC1-AC4 unchecked and all four
TCs implemented. PR #57 remains draft for external review. Final-head CI results
are maintained in its description; no independent signature or merge is claimed.
