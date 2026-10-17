# REQ-029 / HI-S016 proposed store delivery

## Authority and implementation

[human-001][2026-10-17] Instructed “Proceed with HI-S016” after the proposed
scoped-store increment. Accepted REQ-013/015 provide identity and State contracts.
Generator-001 supplies proposed REQ, TC text/code and runtime for combined
external review; no independent workflow signatures are supplied.

Clean implementation source `53939fa5e503715c762e99df70a877dd995fba28` adds a
scoped process-local cache with explicit trusted subject/member/home/role grants,
child read-only restrictions, typed not-found, initially unknown canonical
snapshots, synchronized full-snapshot CAS and detached immutable results.
Elapsed-time ingestion freshness is independent of availability/property times.
Complete one-shot per-home reconstruction validates before atomic publication
and rejects provider-supplied desired intent. Cache revisions reset on restart;
they are not source epochs or durable task state.

Contexts and grants are trusted composition inputs, not authentication tokens.
Northbound callers must derive context from verified identity and trusted policy,
never self-asserted agent/tool parameters. This module has no public route,
physical-device writes, persistence, live-event merging or reconciliation.
HI-S017/018 and HI-S007 remain separately admitted work.

## Executed verification

Linux aarch64 / CPython 3.12.12, source-identical runtime at 53939fa:

- **1110 required fabric + 1795 shared passed**, zero failures/errors/skips.
  The final full fabric rerun includes the completed installed-store smoke wiring
  and tenth-flag mutation guard, with all ten required runtime flags supplied.
- **125 store cases**, including exact scope components, denial before lookup,
  child/read grants, detached inputs/results, typed missing records, per-home
  identical device IDs, CAS conflicts/concurrent winners, strict integer metadata,
  explicit TTL equality, clock regression, partial/invalid-last-state reconstruction
  rollback, desired-intent rejection, one-shot/empty-home and restart semantics.
- Overlapping TC-029-01/02/03/04 groups: **53 / 27 / 44 / 10**. The last group includes
  seven hermetic required-runtime probes. Three additional actual import-blocker
  probes verify 125 optional-absence skips, required absent/broken exit 4 and
  private-detail redaction. Those deliberate optional skips are not part of the
  required suite above.
- **Nine mutations detected** by real pytest assertion failures without timeout:
  grant bypass, cross-home access, write-access bypass, CAS bypass, freshness
  boundary change, clock regression, provider desired intent, reconstruction
  after put, and canonical exception-context disclosure. Exact transformations,
  selections, log/source SHA256, durations and exit codes are retained below.
- Ruff, strict mypy (**15 runtime sources**), governance including **21 planning
  regressions**, ten-flag CI command mutation checks, public-data/requirements
  validation, secret scanning and whitespace pass. All **86** changed Markdown
  local links resolve before the evidence follow-up.

## Clean-source installed packages

Fresh builder records source_dirty:false at 53939fa. Direct and sdist-derived
shared/fabric wheel pairs build and install in fresh isolated environments;
**eight dependency wheels** are verified against official release metadata.
All retained installed checks pass. The four new state-store smokes under
-I / -O -I each report **12 checks, offline:true**, using explicit conditions
that survive optimized Python. The new store source hash, source/artifact/
dependency/JUnit/test/smoke hashes, per-TC counts and mutation probes are in
[machine-readable provenance](REQ-029-artifact-provenance.json).

No local Python 3.13/3.14, Windows/Termux, private HA or hardware result is
inferred. The three-version CI matrix supplies separate runtime and installed
verification; final status is maintained in [draft PR #59](https://github.com/rushwing/ai-family/pull/59).
No accepted HA/shared runtime or historical evidence JSON is modified.

## External review stop

REQ-029 remains req_impl / generator-001, review_round 0, AC1–AC4 unchecked and
TC-029-01–04 implemented. Evidence/link follow-up changes no tested runtime,
test, smoke, dependency or CI bytes. PR #59 remains draft. Human acceptance,
independent review, merge, BUG-033 and Feature/Stage completion retain separate
gates. No next implementation is admitted here.
