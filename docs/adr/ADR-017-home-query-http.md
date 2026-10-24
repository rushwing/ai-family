---
adr_id: ADR-017
title: "Canonical home query HTTP contract and explicit identity composition"
status: proposed
date: 2026-10-23
deciders: [human-001]
informed_by: []
supersedes: null
linked_reqs: [REQ-035]
---

## Context

HI-S028 adds HTTP to accepted REQ-034 queries. Existing product drafts reserve
/api/twin/snapshot and /api/devices/{device_id}; no deployed compatibility
contract exists. ADR-008 identity, ADR-010 governance and ADR-016 canonical
provider separation remain authoritative. The API must authenticate callers
before constructing the trusted RequesterContext expected by the query service.

## Options

### A — Retain prefixed drafts and compose explicit identity/service inputs

**Pros:** preserves product navigation; no duplicate aliases; deterministic
offline verification; exact store grants remain authoritative. Pinned public
keys avoid request-triggered external discovery and token-controlled URLs.

**Cons:** the composition owner must refresh keys, grants and state; no
automatic OIDC discovery or turnkey production deployment in this slice.

### B — Add unprefixed aliases and reuse gateway globals directly

**Pros:** short route spelling and existing network JWKS lookup.

**Cons:** competing contracts; gateway package pulls unrelated Goal tooling;
mutable issuer globals and network lookup complicate isolation and bounded
verification. It does not establish a shared auth library.

## Decision

Propose A for external review. Implement only GET /api/home, /api/areas,
/api/devices, /api/devices/{device_id}, /api/twin/snapshot, with explicit home_id
query scope. The API README records the exact version-1 envelopes and generated
OpenAPI. Device detail aggregates device/state/capabilities; snapshot aggregates
home/areas/devices and an atomic whole-home state capture. Inventory/metadata
are fixed service snapshots; separate calls are not a transaction.

RS256 verification uses explicit issuer/audience/pinned public keys and follows
existing platform role conventions. The store's exact verified-sub/member/role
plus selected-home grant decides access; neither a home query parameter nor
arbitrary token policy fields grant access. No provider calls are exposed.

## Trade-off

Accept explicit app reconstruction for key/policy changes and an app-factory
integration boundary in exchange for deterministic fail-closed composition.
State freshness stays visible even when HA connectivity is unknown. Reads
remain useful before the action path and live bootstrap are implemented.

## Consequences

Add an independently packaged FastAPI app under apps/home-intelligence-api,
HTTP/JWT integration tests, OpenAPI, direct and sdist-derived installed smokes,
and dependency-sensitive CI. Return no-store responses and fixed errors.
The frontend prototype is not automatically connected or deployed. Reuse of
the verifier by other modules or network JWKS refresh requires a later bounded
shared-auth increment. This ADR remains proposed until human review.

## Revisit Trigger

Before production OIDC deployment, define bounded key refresh, revocation,
state bootstrap and operational logging. Revisit aggregation/pagination when
measured household inventory size makes full snapshots impractical. Revisit
authorization when product policy requires device-level grants.

## Review Notes

No independent review yet; generator self-verification is not acceptance.
