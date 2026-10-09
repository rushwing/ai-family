# REQ-016 — Combined TC and Runtime Self-check Evidence

Authority: [REQ-016](../features/REQ-016.md). Human-001 explicitly authorized implementation through req_impl and requested external review afterward. This records Generator self-checks, not independent T07/T10/T13 approval. TC-016-01–06 remain implemented and AC1–AC7 remain unchecked.

## Verification Boundary

Linux aarch64, non-root UID 1000. No provider credentials, live service, device or dispatcher. The DSH PR #32 pre-review of `7405541e` remains human-supplied non-signing Termux / CPython 3.14.6 evidence for the original documentation artifact, not verification of this later Capability runtime.
