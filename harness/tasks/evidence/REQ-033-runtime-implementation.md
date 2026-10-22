# REQ-033 / HI-S015 combined delivery

Human-001 instructed “Proceed with HI-S015” on 2026-10-22 after the proposed
combined specification/test/implementation/draft-PR delivery. generator-001 is
the actual proposed TC text and code author. This is self-verification, with no
independent evaluator or T03/T07/T10/T13 signature. Remain req_impl,
unchecked AC1–AC4 and implemented TC-033-01–04 for external combined review.

## Tested source and results

Clean committed source `3630316340de97cfabc8d180595824c263c0905b`, Linux aarch64 /
CPython 3.12.12. [Verification](REQ-033-verification.json) records JUnit hashes,
executed/passed counts and overlapping TC groups. Full fabric suite: **1690
passed**, zero failures/errors/skips, 78.15 seconds. Shared suite: **1795 passed**,
zero failures/errors/skips, 13.35 seconds. The inference module has **126 cases**;
ten isolated required-runtime gate cases, two isolated normal/optimized smoke
cases and the existing CI-wiring mutation check also cover this increment.

Ruff passed for the complete fabric package/tests. Strict mypy passed all
eighteen runtime modules. scripts/check.sh passed governance and all 21 planning
regressions. Legacy workbook/requirements and public-data checks passed.
Accepted shared contracts and all preceding runtime modules remain identical
to main. CI requires all fourteen runtime flags and exactly 1690 fabric cases.

## Installed artifacts and falsifiers

[Artifact provenance](REQ-033-artifact-provenance.json) records the same clean
source, runtime SHA-256, direct and sdist-derived shared/fabric wheel pairs,
eight officially SHA-256-verified dependency wheels and fresh offline installs.
Both installed pairs passed every existing smoke family. The new inference
smoke ran under -I and -O -I on each pair: four runs, each **16 explicit checks**,
offline:true, rules_version:1. Optimized checks use explicit exceptions, not
assert. The artifact builder ran without --test-results; the separate linked
verification JSON records the source-matching full JUnit reports and TC counts.

The reproducible mutation runner detects **eleven runtime mutations**: wrong
unit, missing absolute-position support, coerced float feature bits, cross-instance
advertisement, wrong parent, disabled entity, ambiguous first-candidate choice,
reversed switch services, incorrect position parameter, result reinitialization
and unsorted capability output. Baseline passes. Each mutant exits 1 with
recorded failures and log hash. Mutations ran before the source commit; runtime
and test hashes match the committed source exactly. No clean-tree execution is
claimed for that earlier mutation run.

## Corrections and execution limits

Initial sandbox full-suite execution had 23 loopback failures / 1667 passes;
an isolated discovery probe confirmed the denied bind on 127.0.0.1. The full
clean-source rerun outside that socket restriction passed all 1690 cases.
Dependency download also initially failed under the network sandbox; the final
builder used explicit external access and a fresh officially verified wheelhouse.
The first shared invocation used an unsupported flag and exited before running
tests; corrected documented invocation passed. Initial planning regressions
needed the newly admitted REQ-033 fixture copied; all 21 then passed.

The first unordered-output mutant survived because tests compared dictionaries.
A literal ordered-ID assertion now detects it. A two-Device same-capability
fixture verifies detached descriptor snapshots and distinct provider routes;
the final code does not reuse container aliases in output JSON.

Only local Python 3.12 was executed for these records. Python 3.13/3.14 results
belong to CI on the final PR head and must be reported separately. No Windows,
Termux, live/private HA, hardware or long-soak certification is claimed.
Capabilities describe metadata support, not observations, authorization or
physical availability. Existing event normalization still requires its explicit
profiles; grouped/extra measurement integration, writes, query/store publication,
reconciliation, BUG-033 and Feature/Stage acceptance remain separate work.

See the sole [REQ-033](../features/REQ-033.md),
[TC-033-01](../test-cases/TC-033-01.md),
[TC-033-02](../test-cases/TC-033-02.md),
[TC-033-03](../test-cases/TC-033-03.md) and
[TC-033-04](../test-cases/TC-033-04.md) for scope and review state.
