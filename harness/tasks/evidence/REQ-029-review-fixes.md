# REQ-029 local pre-review follow-up

The user supplied a non-signing local pre-review of PR #59 head b00f48e and
instructed “Fix all findings”. This generator follow-up closes O1/O2 through
explicit contracts and regressions, retaining O3 as an environment limit. It
provides no T03/T07/T10/T13 approval or final acceptance.

## Dispositions

- O1: At review source bdabd0ddff3031af513142b7527e1e84235efa98, REQ-029,
  TC-029-02/03 and README specify the existing put priority. After authorization,
  device/integer metadata validation and lookup: revision conflict precedes
  elapsed-time regression, which precedes canonical snapshot validation.
  Six compound-error cases assert exact code/path and unchanged payload,
  snapshot and revision. Installed smoke checks stale-revision/regressing-time/
  malformed-payload combinations and verifies the retained snapshot.
- O2: Keep the existing full-snapshot API and accepted shared schema. DeviceState
  carries no completeness/provenance tag, so schema-valid sparse replacements
  and adapter deltas cannot be distinguished. Documentation now explicitly
  states that CAS proves the cache revision, not completeness, and that omitted
  reports / desired_state None replace or clear existing content. A regression
  starts with multiple reports and desired intent, supplies a sparse replacement
  and asserts exact replacement plus an unchanged earlier frozen result. There
  is no claimed runtime delta rejection or implicit merge; callers must prepare
  complete snapshots, with observed-member merging reserved for HI-S017.
- O3: The reviewer's Termux ensurepip limitation remains unchanged. The Linux
  fresh offline installations below and CI are separate evidence. No Termux
  fresh-venv success, new local package build, live HA or hardware claim is made.

## Actual verification

Linux aarch64 / CPython 3.12.12: **1117 required fabric passed**, zero failures,
errors or skips, with all ten runtime flags. **132 store cases**, overlapping
TC-029 groups **53 / 34 / 50 / 10**. Three actual import-blocker probes preserve
optional absence (132 skipped), required absent/broken exit 4 and private-detail
redaction; intentional optional probes are separate from required execution.
The earlier shared suite's **1795 passes** remain source-specific historical
execution; shared runtime is unchanged and this follow-up does not claim a new
local shared-suite rerun. Current CI separately runs the declared shared matrix.

Three isolated source mutations are detected by assertions with pytest exit 1:
clock-before-CAS, payload-before-CAS, and implicit report merging into a full
replacement. Exact source diffs, selections, hashes, duration and results are in
[follow-up provenance](REQ-029-review-fixes-provenance.json). No timeout or skip
counts as detection. Ruff, strict mypy (15 source files), governance including
21 planning tests, ten-flag CI guard, public-data/requirements and whitespace pass.

Production runtime bytes are unchanged: state_store SHA256 remains
b16cb872dc9b535456931c1fe0c28085088b129224476490093386aec59056da.
At clean review source bdabd0d, fresh offline virtual environments install each
retained direct/sdist-derived wheel pair from original source 53939fa, with the
previously officially verified eight-dependency wheelhouse. Both wheel payloads
match the unchanged store runtime hash. The updated smoke is copied outside the
checkout and passes all four -I / -O -I runs: **15 checks, offline:true** each.
These artifacts were reused, not rebuilt; original provenance JSON is preserved.
CI additionally builds/installs the current declared three-version package matrix.

## External review boundary

REQ-029 stays req_impl / generator-001, review_round 0, four unchecked ACs and
four implemented TCs. PR #59 remains draft; final-head CI status is maintained
in the PR description. The pre-review's reported 1110/1795 Termux passes and
11 detected mutations are attributed reviewer results at b00f48e, not execution
of this follow-up and not independent workflow signatures. No merge, acceptance
or next increment is inferred.
