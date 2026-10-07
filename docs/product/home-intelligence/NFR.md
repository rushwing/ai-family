# Non-functional Requirements

## NFR-HI-001 — Reliability

**Requirement:** Connection loss changes health and freshness; bounded reconnect plus snapshot reconciliation restores current state.

**Verification:** Fake HA disconnect/reconnect integration test; controlled R1 demo.

**Applies to:** HI-F001/002/006

## NFR-HI-002 — Security

**Requirement:** All protected reads/writes use trusted identity and scoped access; unsupported operations fail closed before provider dispatch.

**Verification:** Negative JWT/role/member/device tests and zero-provider-call assertions.

**Applies to:** HI-F008/010

## NFR-HI-003 — Privacy

**Requirement:** Secrets and real household inventory remain private; logs redact credentials and sensitive arguments. Camera processing is local-first with consent and retention boundaries at R9.

**Verification:** Secret/public-data checks; redaction assertions; later R9 privacy acceptance.

**Applies to:** All stages

## NFR-HI-004 — Observability

**Requirement:** Every action task has task_id and trace_id; completion, denial, timeout and errors correlate across API/guard/provider/audit.

**Verification:** Integration test correlating task result and durable audit records.

**Applies to:** HI-F007/008/010

## NFR-HI-005 — Offline Degradation

**Requirement:** Offline devices remain readable with last observation/freshness; unsafe writes are rejected; unavailable state is not reported as healthy.

**Verification:** Offline state/query/action negative tests.

**Applies to:** HI-F002/006/008

## NFR-HI-006 — Idempotency

**Requirement:** The same scoped idempotency key and action payload cannot create repeated physical dispatch; changed payload under the same key is rejected. Unknown irreversible outcomes require reconciliation.

**Verification:** Duplicate/concurrent/restart dispatch tests; uncertain-feeding checks in R2.

**Applies to:** HI-F007/008; R2

## NFR-HI-007 — Latency

**Requirement:** Action submission returns an accepted task response without waiting for physical completion; reconnect and action waits obey documented finite configuration bounds.

**Verification:** Fake clock tests at configured deadlines; record API duration in the controlled demo.

**Applies to:** HI-F001/007/010

## NFR-HI-008 — Recoverability

**Requirement:** Current state reconstructs after restart; action/audit/confirmation data survives restart; workflow recovery reconciles durable business state.

**Verification:** Restart and crash-injection tests against real PG/queue where required.

**Applies to:** HI-F006/008; HI-F102

## NFR-HI-009 — Auditability

**Requirement:** Allowed/denied actions produce durable redacted append-only evidence; app roles cannot alter/delete it and reads enforce scope.

**Verification:** PostgreSQL permissions/RLS and audit-failure integration tests.

**Applies to:** HI-F008/109

## NFR-HI-010 — Boundary Integrity

**Requirement:** Agent/workflow code uses canonical capabilities and cannot invoke arbitrary HA services, MQTT topics or vendor IDs; all writes use the governed path.

**Verification:** Contract tests and import/API review, including negative bypass attempts.

**Applies to:** All stages

## Measurement Policy

Do not invent unmeasured production SLOs. Timeout/reconnect limits must be finite, documented and tested. Record latency and outage evidence in R1; set numeric operational SLOs from that evidence before declaring production readiness. Baseline requirements apply immediately, even when R11 operations are still planned.
