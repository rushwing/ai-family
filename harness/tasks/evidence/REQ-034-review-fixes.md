# REQ-034 local pre-review follow-up

Human-001 supplied a local pre-review report for PR #69 at head 2b973c2 and
instructed “fix all findings.” The report explicitly supplies no independent
T03/T07/T10/T13 approval. The following are generator-001 corrections and
self-verification. REQ-034 remains req_impl, ACs unchecked, four TCs implemented
and PR #69 draft.

## Dispositions

- O1: public QueryResult construction now validates its entire envelope using
  the accepted bounded plain-JSON validator. Unsupported objects, bytes, tuples,
  sets, non-string keys, nonfinite numbers, invalid UTF-8, oversized integers,
  aliases/cycles and excessive depth fail with redacted
  HomeQueryError(invalid_configuration), without retained cause/context.
  Status validation retains its existing ValueError. Valid JSON stays detached;
  process-control exceptions propagate. The REQ and package README describe
  these public construction limits.
- O2: store invalid_identifier now maps to invalid_selector, consistently with
  the service's own selector validation. A forced store error covers this
  defensive path even though current public selectors are prevalidated.
- O3: the historical verification JSON actually contains non-null exit_code
  values (baseline 0, eleven mutants 1); it does not contain returncode:null.
  Preserve that source-specific evidence unchanged. New mutation runner output
  uses the subprocess field name returncode; the follow-up verification embeds
  the new report without field-name translation.

## Verification

The query module now contains 185 cases (16 added); full CI baseline is 1888.
The mutation baseline passes and all thirteen mutants are detected, including
two new falsifiers for omitted result validation and misclassified identifiers.
The installed query smoke adds unsupported-object and NaN rejection, now
22 explicit checks per normal/optimized run on each wheel pair.

Ruff, strict mypy (nineteen modules), governance and 21 planning regressions,
public-data and legacy-requirements checks pass. Full-suite and installed-artifact
counts, hashes and tested source are in the linked follow-up verification and
artifact provenance. Original evidence remains historical and source-specific;
runtime bytes have changed since 702d407, while accepted state_store.py and
shared-contract sources are unchanged by these corrections.

The first targeted run had 184 passes and one failure because the new injected
StateStoreError fixture omitted its required path argument. Correcting the
fixture produced 185 passes. No runtime behavior was changed for that fixture
correction. The first full run had 1886 passes and two failures because the
isolated smoke gate still expected 20 checks; it now correctly expects 22 before
the full rerun.

## Supplied report and limits

The human's Android/Termux aarch64 / CPython 3.14.6 report states 1872 fabric and
1795 shared passes at the prior head, confirms all eleven original mutants and
five additional mutants were detected, and describes nine groups of additional
functional/concurrency probes. These are supplied local pre-review observations,
not execution performed here and not an independent approval signature.

Our follow-up execution is Linux aarch64 / CPython 3.12.12. Final-head CI across
3.12/3.13/3.14 is recorded separately in the PR. Windows/BUG-033, live HA, hardware,
long-soak validation, HTTP/authentication, device writes and Feature/Stage
acceptance remain outside this correction.


Follow-up evidence: [verification](REQ-034-review-fixes.json) and
[installed artifacts](REQ-034-review-fixes-provenance.json). Clean tested source
`ea75814dbae324d8cdae4baa91f17267ef065ef2`: **1888 passed**, zero failures,
errors or skips. Direct and sdist-derived pairs passed all smoke families,
including four query runs with **22 checks** each. Eight dependency wheels were
verified against official release digests. Subsequent commits add evidence only.

Implementation-head [CI run 39910098558](https://github.com/rushwing/ai-family/actions/runs/39910098558)
passed at `ea75814dbae324d8cdae4baa91f17267ef065ef2`: all eleven selected
jobs passed, including shared-contract and fabric suites and installed-package
checks on Python 3.12/3.13/3.14. The unrelated web and legacy-workbook jobs
were skipped by path filters. Evidence-only PR-head CI is checked separately.
