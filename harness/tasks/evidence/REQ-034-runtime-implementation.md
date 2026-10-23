# REQ-034 / HI-S018 combined delivery

Human-001 authorized the combined scoped-query delivery on 2026-10-22 and
instructed continuation on 2026-10-23. generator-001 authored the proposed TC
text, implementation and this self-verification. REQ-034 remains req_impl,
AC1–AC4 unchecked and TC-034-01–04 implemented for external combined review.
No independent evaluator or T03/T07/T10/T13 signature is asserted.

## Tested source and results

Clean source `702d407646134062c253c32e142c022bd0d71435`, Linux aarch64 /
CPython 3.12.12. [Verification](REQ-034-verification.json) records source hashes,
JUnit hashes, totals, overlapping TC groups and mutation results. The previous
session's same-source reports record **1872 fabric tests** and **1795 shared
contract tests** passing with zero errors, failures or skips. The query module
contains **169 cases**. TC groups overlap and must not be summed as unique tests.

On 2026-10-23 Ruff passed the complete fabric package/tests and strict mypy
passed all nineteen runtime modules. Governance/planning, public-data and
legacy-requirements checks are run again for the evidence delivery. Shared
contract sources are unchanged from main. CI requires all fifteen runtime flags
and exactly 1872 fabric cases across Python 3.12/3.13/3.14.

## Installed artifacts and falsifiers

[Artifact provenance](REQ-034-artifact-provenance.json) records the 2026-10-23
clean-source build, both full JUnit summaries, direct and sdist-derived
shared/fabric wheel pairs, eight dependency wheels verified against official
release SHA-256 values and fresh offline installations. Both installed pairs
passed all smoke families. Query smokes ran with -I and -O -I on each pair:
four runs, each **20 explicit checks**, offline:true. Checks survive optimized
execution. Runtime source, wheel and dependency hashes are included.

The reproducible mutation runner's clean-source baseline passes and all
**eleven mutations** are detected: authorization bypass, ignored area filter,
reversed device ordering, cross-home capability disclosure, metadata-created
inventory membership, absent metadata treated as empty, exclusive freshness
boundary, stale treated as fresh, duplicate metadata records, result
reinitialization and unlocked snapshots. The retained report records source
identity and individual log hashes; runtime/store/test hashes match this source.

## Execution limits and review handoff

The previous package runs timed out while fetching official dependency release
metadata. The fresh 2026-10-23 rerun with authorized network access completed
without changing runtime or bypassing dependency verification.

Local execution covers Linux aarch64 / CPython 3.12 only. Final PR-head CI on
Python 3.12/3.13/3.14 is separate evidence. Windows/BUG-033, live/private HA,
physical devices and long-soak behavior are not certified. Requester contexts
are trusted composition inputs; authentication, HTTP routes, durable policy,
reconnect reconciliation, device writes and Feature/Stage acceptance remain
separate work. HI-S028 is a future candidate after this delivery's acceptance.

The sole engineering specification is [REQ-034](../features/REQ-034.md).
Subsequent delivery commits add evidence/navigation only; implementation and
test code remain at the tested source above. The draft PR supplies the external
combined-review artifact; this delivery does not authorize merge or acceptance.
