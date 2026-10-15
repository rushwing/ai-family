# PR #51 post-merge findings — REQ-025 follow-up

Human-001 supplied the post-merge report and instructed “Fix all findings” on
2026-10-15. This is generator-001's implementation/disposition evidence, not an
independent T03/T07/T10/T13 signature. REQ-025 remains req_impl, new TCs implemented
pending external review. Archived REQ-024, its accepted ACs/passing TC records and
all prior provenance files remain unchanged.

## Finding disposition

| Finding | Change and verification | Remaining limit |
| --- | --- | --- |
| F1 | Source regression inspects the actual client TLS context and requires nonempty trusted roots. Installed smoke uses explicit require(), including -O -I, and records loaded_ca_count=121 rather than relying only on a hash of certifi.where(). Removing CA loading fails the source test and optimized smoke. | This inexpensive positive-root assertion does not claim a live production WSS handshake. Existing self-signed/ambient-override rejection remains effective. |
| F2 | Event-gated auth recv exposes cancellation after aclose sets closed. Releasing cancellation must leave the exact immutable snapshot and sequence unchanged; every observed post-close snapshot equals the first closed snapshot. Removing the publish guard fails by assertion. | Polling health remains a current snapshot, not a new historical-event API. |
| Deadline mutation | Add a one-second wait_for and finally-close to the existing expiry regression. Removing the explicit deadline check now fails in about 1.7 seconds with pytest TimeoutError, not an outer process timeout. | This is a bounded test falsifier, not a production timing SLO. |
| F3 / BUG-032 | Fresh wheelhouse, official explicit index, disabled pip config/PIP_* option overrides/cache; verify every dependency wheel against exact-filename official release SHA256 before any installation. Store verified URLs/digests and sanitized acquisition policy/log identities. Hermetic failure tests reject tampering, missing/duplicate/sdist entries, bad digest/mirror URL, extra/empty files and unavailable/malformed/redirected/oversized metadata. | Retained historical archives/logs were subsequently recovered. All three match the recorded digests and current piwheels downloads; the recovery audit identifies mixed-index packaging as the cause. BUG-032 is resolved with original records preserved; no signed custody or historical runtime rerun is claimed. |
| F4 | New REQ-024-final-provenance.json records a clean fresh source commit, actual runtime/file/artifact/dependency digests, official metadata response digests, JUnit totals/per-TC counts and direct/sdist-derived installed checks. Runtime byte identity is checked against accepted merged main and both newly built fabric wheels. | This is new execution at e363505, not retroactive artifact provenance for a006c975. Existing prose/CI evidence for that historical execution remains historical. |
| F5 | PR #51 now states merged 2d986a7 and human final acceptance, with the prior stop superseded. PR #52 now states merged 02c6e3a. Both saved descriptions were read back and verified. | No independent Harness signature is introduced. |
| F6 | Preserve prominent Windows limitations and BUG-033. | No Windows execution or portability fix is claimed by this follow-up. |

## Actual source and execution

Implementation/test/CI/artifact source:
`e363505d9303be345dcb44fa726595a49086c5a2`.
Subsequent commits add delivery/provenance records only. Tests ran against the
same implementation tree committed at that source. The builder recorded a clean
source checkout. Platform: Linux aarch64, CPython 3.12.12; no local 3.13/3.14,
Windows, Android or live HA execution is claimed.

- Full six-flag required fabric suite: **717 passed**, zero failures/errors/skips.
- Full six-flag required shared-contract suite: **1795 passed**, zero failures/errors/skips.
- Governance, fabric CI wiring and **21 planning tests** pass; Ruff and strict mypy pass.
- Direct and sdist-derived wheel pairs build and install in fresh /tmp venvs;
  all retained provider/demo/conformance/configuration/REST smokes pass, as do
  four new lifecycle smokes (two pairs × -I / -O -I). Each actual client context
  contains 121 CA roots; exact auth count is four per lifecycle smoke.
- Eight downloaded dependency wheels match their official PyPI SHA256 values.
  Metadata failures are fatal; raw pip logs/environment values are not published.
  Hashes and verified URLs comprise the sanitized acquisition record.
- TC group counts in the new JSON: TC-025-01=3, TC-025-02=18, TC-025-03=5.
  Groups overlap; they are not summed as suite totals. Existing TC-024-04/05
  grow by one each; the archived TC documents retain their historical acceptance.

[Machine-readable final evidence](REQ-024-final-provenance.json) includes source,
platform/interpreter, runtime SHA256, paired-artifact hashes, dependency closure,
upstream metadata and artifact URLs/digests, JUnit digests and exact TC counts.
Runtime SHA256 is
`f23f6600190c362e795039fa8d15f628781ddc1581778ebc12628259e7d092f5`, identical to
accepted merged REQ-024 and both new installed-package wheel payloads.

Commands (Python is /tmp/req019-env/bin/python):

```text
python -m pytest -c toolsets/iot/home-device-fabric/pytest.ini toolsets/iot/home-device-fabric/tests --require-provider-runtime --require-demo-runtime --require-conformance-runtime --require-ha-configuration-runtime --require-ha-rest-runtime --require-ha-websocket-runtime -q --junitxml=/tmp/req025-fabric-pre.xml
python -m pytest libs/state-schema/tests --require-inventory-runtime --require-binding-runtime --require-state-runtime --require-capability-runtime --require-initial-capabilities-runtime --require-action-runtime -q --junitxml=/tmp/req025-shared.xml
python toolsets/iot/home-device-fabric/tests/build_artifacts.py --out-dir /tmp/req025-final-artifacts --test-results /tmp/req025-fabric-pre.xml --test-results /tmp/req025-shared.xml
bash scripts/check.sh
ruff check toolsets/iot/home-device-fabric
mypy --config-file toolsets/iot/home-device-fabric/pyproject.toml toolsets/iot/home-device-fabric/src
python tools/check_home_intelligence_requirements.py
python tools/check_home_intelligence_public_data.py
```

Loopback suites/build smokes ran outside the restricted network sandbox because
it prevents binding local TCP ports. An earlier sandbox attempt failed at bind;
it is not counted as a product failure or passing run. The first new ZIP fixture
used ambient timestamps and failed its offline guard; it now uses an explicit
fixed ZipInfo date and the guard remains intact.

## Mutation execution

Separate Python processes execute the real imported runtime with one in-memory
source mutation, then the named real regression through pytest.main. No tracked
runtime file is edited. Each subprocess has an outer 15-second safety timeout;
none hit it. Missing CA load and publication guard each return pytest exit 1
with one failed test (approximately 0.7/0.6 seconds). Missing final deadline check
returns pytest exit 1 with one failed test (approximately 1.7 seconds). Removing
CA load also returns exit 1 from the installed-style explicit-require smoke under
-O -I. Machine results are included in the final provenance. No outer timeout
is counted as a detected mutation, and no optimized pytest run is used as evidence.

## Upstream basis and historical limits

[PyPI release JSON](https://docs.pypi.org/api/json/) supplies exact release file
digests; [pip configuration](https://pip.pypa.io/en/stable/topics/configuration/#pip-config-file)
documents that PIP_CONFIG_FILE=os.devnull disables configuration files. These
support the new acquisition policy, not recovery of historical bytes. The
human's additional PyPI/sdist/PEP-658 comparisons are attributed in BUG-032.

[REQ-025](../features/REQ-025.md) owns this proposed increment; no product Story
is re-admitted and no historical acceptance is revoked. The follow-up PR remains
draft and unmerged pending review and explicit human acceptance.

## Subsequent historical recovery

[Recovery audit](REQ-023-recovered-wheel-audit.json) supersedes the earlier
unrecovered-bytes assumption: nine retained download logs identify piwheels;
three historical hashes match both retained archives and read-only fresh
piwheels downloads. anyio/certifi have identical member bytes, with ZIP timestamps
differing. h11 differs only in WHEEL generator metadata, its RECORD and ZIP
timestamps; all Python payloads match the official PyPI wheel. BUG-032 is resolved
as an archive-origin discrepancy caused by mixed-index acquisition. Retained
logs are corroborating evidence, not signed custody. No old provenance or
archived acceptance is changed, and no historical execution is re-certified.

Final source-equivalent CI run 38672365534 at delivery head 20f986c passed all
11 applicable jobs, including Python 3.12/3.13/3.14 fabric/shared/artifact matrices;
two unrelated product jobs were path-filtered. This later recovery append changes
evidence and bug disposition only, not the tested implementation.
