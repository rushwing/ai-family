# REQ-032 local pre-review response O1–O3

[generator-001][2026-10-19] Human-001 supplied a non-signing local pre-review of
PR #65 head `38ca7c5f` and instructed “Fix All Findings”. All three observations
are addressed on clean source `47be5b909cd48f7dc3016fc0d8a768a9f90a2043`.
This record supplies execution evidence, not independent evaluator approval,
human final acceptance or a lifecycle signature.

## Dispositions

**O1 — direct result construction:** retain the exported HAMappingResult API,
but eagerly validate exact string inputs and bounded strict JSON (including
duplicate fields, nonfinite values and Unicode), accepted Inventory and
BindingCollection shape/references, an exact twelve-member tuple of exact
integer counters in 0..10000 and matching area/device/binding cardinalities.
Only publish immutable fields after all validation succeeds. Invalid initial
values raise finite context-free invalid_projection/input_limit at construction.
Valid direct instances export detached normalized data; reinitialization with
otherwise valid replacement data remains forbidden. Structural validity does
not prove execution history or origin of caller-supplied data.

Thirty-four new cases cover malformed direct inputs, JSON bounds, cardinalities,
valid direct instances and invalid binding references. Counter tests keep other
values valid so shape/cardinality failures cannot mask type/range/length checks.
The existing reinitialization case now uses valid replacement data. Three new
runtime mutations bypass counter type, length or cardinality validation and
are each detected by assertions.

**O2 — reserved grouped-entity assignments:** README, REQ and TC-032-02 now
explicitly state that entity_ids assignments for entities with device_id remain
reserved and participate in global uniqueness without creating independent
Devices. They become usable if the entity later has no device_id; they do not
bypass missing/unassigned/disabled-parent exclusion. A new case uses one mapper
across grouped-to-standalone inputs and checks literal IDs and binding fields.

**O3 — unresolved-area count:** README, REQ and TC-032-02 define unresolved_areas
as unresolved nonnull references per emitted Device, including standalone
Devices. It is not distinct missing areas or grouped entities. Null references
and omitted Devices do not contribute. Two new cases cover a missing area and
a present-but-unassigned area shared by a grouped Device and a standalone
Device: both yield exactly two, despite three underlying entity rows.

## Source-specific execution

Linux aarch64 / CPython 3.12.12, compatible editable packages in
`/tmp/req032-env`. [Verification](REQ-032-review-fixes-verification.json) retains
commands, file hashes, TC groups, log digests and reproducible mutation outcomes.

- **1552 fabric passes**, all thirteen required-runtime flags, zero failures,
  errors or skips, 68.08 seconds. **1795 shared passes**, all six flags,
  zero failures/errors/skips, 10.39 seconds.
- **121 mapper cases**, including 37 new cases; TC groups **4 / 20 / 97 / 13**.
  **134 targeted checks** pass; ten isolated runtime-gate probes now expect all
  121 actual mapper cases to skip when optional runtime is absent/broken.
- The checked-in disposable-copy mutation runner detects all **eleven runtime
  mutations**: the original eight rerun on amended source plus three O1 counter
  mutations. The clean baseline passes all 121 mapper cases. Mutation execution
  preceded the source commit; recorded runtime/test hashes match its bytes.
- Ruff, strict mypy (17 runtime sources), all nine governance/requirements
  scripts and all 21 planning regressions pass. CI retains thirteen required
  flags and raises the installed-artifact expected count from 1515 to **1552**.

[Fresh artifact provenance](REQ-032-review-fixes-artifact-provenance.json)
records clean source, both passing JUnit totals, eight officially verified
dependency wheels, fresh direct and sdist-derived shared/fabric wheel pairs,
offline fresh-environment installs, pip check and all installed smoke families.
Four mapper smokes under normal/optimized isolated Python each pass **16 explicit
checks**, reporting offline:true and rules_version:1. New installed checks cover
valid direct construction, eager count-length rejection, reserved grouped
assignment and shared unresolved-area references. Full-suite and fictional
loopback smokes ran with explicit sandbox authorization.

## Attribution and limits

The user-supplied non-signing report attributes 1515 fabric / 1795 shared passes,
84 mapper cases, eight author mutations plus five additional reviewer mutations
and custom probes to Android/Termux aarch64 / CPython 3.14.6 at `38ca7c5f`.
These remain attributed results for that earlier head. They do not verify the
amended runtime or represent generator execution, independent lifecycle approval
or a new Termux/Windows result. No live/private HA or physical-device result is
claimed. Final-head CI supplies the amended Python 3.12/3.13/3.14 matrix.

All 29 evidence JSON files present at reviewed head `38ca7c5f` remain unchanged.
Original local shared/wheel evidence and the collection-fix record keep their
actual source/counts; fresh results above do not retag historical executions.
Nine preceding accepted runtime modules and shared contracts remain unchanged.
O1 is the only production runtime change; O2/O3 clarify existing semantics.

[REQ-032](../archive/done/features/REQ-032.md) stays req_impl / generator-001, review_round 0,
four unchecked ACs and four implemented TCs in
[draft PR #65](https://github.com/rushwing/ai-family/pull/65). This response does
not authorize merge, done archival, Feature/Stage completion or the next Story.
