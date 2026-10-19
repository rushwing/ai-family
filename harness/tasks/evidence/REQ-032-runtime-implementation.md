# REQ-032 / HI-S014 proposed canonical registry mapper

The [collection-gate follow-up](REQ-032-collection-fix-verification.json)
records amended test source `f66ab43` and a fresh 1515-case fabric pass. Final
self-review moved mapper/shared imports inside test execution so optional
runtime absence is classified before fixtures execute. Missing/broken/dependency
gate probes now collect the actual mapper test module rather than only toy
probes. All 97 targeted checks and eight runtime mutations pass their intended
assertions. Production/runtime/build code is unchanged. Original local shared
and wheel-pair evidence below retains its actual source; fresh amended-source
wheel-pair verification belongs to final PR CI.

[generator-001][2026-10-19] Human-001 explicitly instructed “Proceed with
HI-S014” after clarifying the HI-S015 dependency. This is a generator-authored
combined specification, proposed TC and runtime delivery for external review.
No independent evaluator signatures or final human acceptance are claimed.

## Design and boundary

`HARegistryMapper` accepts an explicit trusted Home/instance alias and separate
provider-to-canonical area/device/standalone-entity assignments. The caller
allocates and retains identities; the mapper never derives canonical identity
from provider IDs, hashes or names. Replacing provider keys/instance aliases
while retaining canonical assignments preserves canonical inventory identity.

The pure synchronous mapper validates a bounded complete four-list discovery
export, then builds accepted Inventory and BindingCollection records. Enabled
entities on a registry device share one Device and sorted binding membership.
Explicitly assigned entities with no registry device may form standalone
Devices. Missing/unassigned/disabled referenced devices are never implicitly
promoted. Missing areas yield null locations. Grouped devices use the registry
device's area; entity overrides do not split or relocate it. No floor/type or
capability inference is performed. Provider names are projected using explicit
precedence and a neutral fallback, with private repr and count-only summaries.

Each call is a fresh projection, not a store merge. Entity removal shrinks
binding membership and removes an empty Device from this result; assignment
retention restores identity on reappearance. No deletion command, tombstone,
physical availability, epoch or automatic store-replacement policy is implied.

Configuration/results are detached immutable private snapshots with refused
copy/pickle/reinitialization and explicit `for_adapter()` export. Full-input
validation includes otherwise ignored state/extra JSON data. Finite errors are
raised outside raw exception handlers to discard exception context; shared
factory details and submitted values do not enter ordinary diagnostics.
Process-control exceptions propagate. Private introspection, traceback locals
and deliberate private exports remain outside redaction.

## Exact local execution

Tested source: `d3b941a93c32f2cc00f365c170be3d158528a47c`, clean working tree.
Linux aarch64 / CPython 3.12.12, compatible editable shared/fabric packages in
`/tmp/req032-env`. [Verification](REQ-032-verification.json) records commands,
source hashes, logs, TC counts and the reproducible disposable-copy
[mutation harness](../../../toolsets/iot/home-device-fabric/tests/ha_mapping_mutations.py).

- Required fabric suite, all thirteen flags: **1515 passed**, zero
  failures/errors/skips, 67.31 seconds.
- Required shared suite, all six flags: **1795 passed**, zero
  failures/errors/skips, 11.31 seconds.
- **84 mapper cases**. Overlapping TC-032 groups: **4 / 17 / 63 / 13**.
- Ten isolated gate cases cover absent/broken modules, absent callable/dependency,
  optional skips, mandatory skip failure and valid execution. Required module
  failures exit 4; mandatory skips exit 1. All thirteen CI flag removals and
  command/job falsifiers are detected.
- Eight runtime mutations fail by assertions: ambiguous identity acceptance,
  retaining only the last grouped entity, including disabled entities, unsorted
  binding membership, dropping spatial assignment, skipping state validation,
  allowing result reinitialization and allowing aliased dicts. Their clean
  baseline passes all 84 mapper cases. Execution preceded source commit, but
  runtime/test hashes match that committed source exactly.
- Ruff and strict mypy pass for all **17 runtime sources**. All nine
  governance/requirements scripts and **21 planning regressions** pass.

Before the committed source, two smoke-logic tests exposed a harness import
ordering issue: importing the gate helper under ambient denial captured the
blocked subprocess launcher. Moving those tests into the existing gate module
restored its normal capture-before-fixtures behavior. All final committed tests
passed. Full-suite and installed fictional loopback operations ran with explicit
sandbox authorization; mapper calls themselves require no ambient effects.

## Installed packages and provenance

[Artifact provenance](REQ-032-artifact-provenance.json) records clean tested
source, Python/platform, exact artifacts and dependency hashes, JUnit totals and
smoke results. The existing builder acquired and verified eight dependency wheels
against official release metadata, built fresh shared/fabric direct wheels and
sdists, rebuilt wheels from extracted sdists, and installed both compatible pairs
into fresh environments with offline dependency installation and `pip check`.

All existing installed smoke families passed. Four mapper smokes (direct and
sdist-derived pairs under `-I` and `-O -I`) each passed **13 explicit checks**,
reporting `offline:true`, `rules_version:1`. Those checks survive optimized
Python and verify actual installed code, not editable package imports. Both
fabric/shared suite totals are retained in artifact provenance. CI preserves
all thirteen required flags and expects 1515 installed-artifact fabric cases.

## Scope and lifecycle limits

The sole [REQ-032](../archive/done/features/REQ-032.md) remains req_impl / generator-001,
review_round 0, ACs unchecked and TC-032-01–04 implemented in
[draft PR #65](https://github.com/rushwing/ai-family/pull/65). Local evidence
covers Linux aarch64 / Python 3.12.12 only. Final PR CI owns Python 3.13/3.14 and
fresh runner artifact verification. No new Windows/Termux, live HA, credentials,
hardware, long-soak or independent reviewer result is inferred.

Accepted shared contracts and previous runtime modules are unchanged. Automatic
identity allocation/persistence, cross-instance aggregation, capability inference,
state-store publication, query/API services, reconnect reconciliation, device
actions, BUG-033 and Feature/Stage completion remain separate work. Updating the
trusted assignment configuration and retaining prior assignments is the caller's
responsibility; rolling back this module does not reconcile an external store.
