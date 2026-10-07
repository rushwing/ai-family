# Shared Definition of Done

Story acceptance decides the specific increment; this document supplies the common engineering completion gate. Product Story completion derives from its admitted Harness REQ and does not bypass that lifecycle.

- [ ] All acceptance criteria are verified with evidence identifying the tested commit and environment.
- [ ] The bounded increment is implemented and remains independently mergeable; unfinished functionality is not exposed as successful behavior.
- [ ] Relevant unit tests are added or updated, including meaningful failure cases. Documentation-only work records why runtime tests do not apply.
- [ ] Relevant integration/contract/e2e tests actually pass; required skipped tests do not count as delivery evidence.
- [ ] Applicable lint, static/type checks and existing governance gates pass; unsupported check categories have an explicit reason.
- [ ] Authorization, isolation, confirmation, idempotency and physical completion semantics are verified wherever affected.
- [ ] Operationally relevant logs/errors include correlation IDs and redact secrets and private household information.
- [ ] Configuration, private secret handling, public API changes and failure/recovery behavior are documented.
- [ ] Product documents, machine index, shared contracts, relevant ADR references and migration/rollback guidance are synchronized.
- [ ] Architecture boundaries hold; no direct Agent/Workflow provider calls or vendor identifiers leak into canonical contracts.
- [ ] No known critical/high defects affecting this increment remain unresolved; all linked req_bug and review blockers satisfy Harness done rules.
- [ ] TC/BUG/PR/release evidence is linked through the REQ; the independent Evaluator verifies implementation and required live environments.
- [ ] The PR is merged through the existing human-controlled Harness flow; prototype-only behavior is not labeled complete.

Physical reversal is not assumed possible. Where a migration or device action cannot be rolled back, document reconciliation, compensation or manual recovery instead of promising a fictitious undo.
