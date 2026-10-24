# Canonical Home Query API

REQ-035 / HI-S028 supplies an explicitly composed FastAPI app over the accepted
canonical query service. This is an offline-verified HTTP increment awaiting
external combined review. It is not a deployed/live home integration.

## Version-1 route proposal

All protected routes require `Authorization: Bearer <access-token>` and exactly
one canonical `home_id` query parameter. IDs use `^[a-z][a-z0-9_-]{0,63}$`.

| GET route | `data` in the found envelope |
| --- | --- |
| `/api/home` | Canonical Home |
| `/api/areas` | Canonical Area list, sorted by ID |
| `/api/devices` | Canonical Device list, sorted by ID; optional `area_id` |
| `/api/twin/snapshot` | `{home, areas, devices, states}` |
| `/api/devices/{device_id}` | `{device, state, capabilities}` |

Success: HTTP 200, `{"status":"found","data":...}`. Missing device or area
filter: HTTP 404, `{"status":"not_found","data":null}`. A known empty area
returns 200 with `data:[]`. The selected home must match an exact configured
caller grant; unknown and unauthorized homes both return 403.

`state` and each element of `states` is the accepted StateView:
`{status:"found",state,revision,updated_at_ms,freshness}`. State retains
`home_id`, `device_id`, `desired_state`, `reported_state` and `availability`.
Freshness is `uninitialized`, `fresh` or `stale`; the configured age boundary
is inclusive. Offline/stale state remains readable. Missing observations stay
unknown and are never converted to zero/false. Capability metadata is
`{status:"found",data:[descriptors...]}` or
`{status:"uninitialized",data:null}`. Descriptors contain the accepted canonical
properties/actions/events and imply neither current availability nor write
permission. HA entity IDs and provider bindings are absent.

Snapshot captures all state rows under one store lock. Its inventory and the
service's capability metadata are fixed at service construction. Separate
HTTP calls are not one transaction. `/api/twin/snapshot` is a canonical backend
projection, not the frontend prototype's fictional graph/nodes or layout.
Frontend adaptation is a subsequent integration step.

`/openapi.json`, `/docs` and `/redoc` expose static documentation without tokens
or household inventory. The checked-in [OpenAPI contract](openapi.json) must equal the schema generated from response models, HTTPBearer
security and explicit query parameters. There are no unprefixed aliases,
state/event streams, task endpoints, device writes or CORS defaults. Proposed
[ADR-017](../../docs/adr/ADR-017-home-query-http.md) records compatibility and
identity composition for review; ADR-010/016 boundaries remain authoritative.

## Identity and composition

Install local dependencies, then provide a private composition module:

```sh
python -m pip install -e libs/state-schema -e toolsets/iot/home-device-fabric
python -m pip install -e 'apps/home-intelligence-api[serve,test]'
```

```python
from home_device_fabric.home_queries import HomeQueryService
from home_device_fabric.state_store import CurrentStateStore
from home_intelligence_api import TokenVerifier, create_app

# These inputs are supplied by trusted private configuration, not request JSON.
store = CurrentStateStore(inventories=canonical_inventories, grants=explicit_grants)
service = HomeQueryService(store=store, capabilities=canonical_capability_records)
verifier = TokenVerifier(
    issuer="https://idp.example/realms/family",
    audience="home-api",
    public_keys={"configured-key-id": trusted_rsa_public_pem_bytes},
)
app = create_app(service=service, verifier=verifier, max_age_ms=30000)
```

Run your composition with `uvicorn private_composition:app`. No default app or
fixture grants are exported. Terminate TLS at the existing private ingress;
configure finite server request/header timeouts and disable unredacted access
logs that include household selectors. This package emits no application logs
or token-bearing error details. Transport/ingress logging remains an operator
responsibility. No network endpoint or credential is inferred from environment.

The verifier requires RS256, a configured `kid`, exact issuer/audience, integer
`iat`/`exp`, valid optional `nbf`, nonempty `sub` and `family_member_id`, and one
unambiguous `admin`/`adult`/`kid` role. The gateway aliases `best_pal` → `admin`
and `go_getter` → `adult` are preserved. Realm roles and a direct role claim
must agree on exactly one platform role. Other token policy claims and identity
headers do not grant access. No token-controlled key URL is followed; there is
no runtime JWKS fetch. Trusted public key rotation requires a new verifier/app.

The API constructs RequesterContext from verified subject/member/role and the
explicit home selector; the store's exact four-part grant remains the authority.
An admin has no implicit all-home access. Kid callers need an explicit read
grant. Current accepted grants are home scoped; device-level policies are not
claimed. Rebuild the service/app for grant revocation and metadata changes;
replace running instances atomically and drain old instances during rotation.
No mutable global key or policy registry is shared between app instances.

Freshness uses a server clock, Unix milliseconds by default, with a finite
`max_age_ms` between 0 and 86,400,000. Store writes must use the same clock
domain. Tests may inject a trusted clock. Clients cannot supply time, freshness,
identity or extra query fields. Live ingestion, reconnect reconciliation and
health-monitor wiring remain composition work; freshness does not assert HA
connection health. REQ-026 health remains independently available.

## Errors and privacy

Errors contain only `{"error":{"code":"..."}}`:

| HTTP | Code |
| --- | --- |
| 400 | `invalid_request` (missing/duplicate/extra query fields, malformed selector or GET body) |
| 401 | `unauthenticated` plus `WWW-Authenticate: Bearer` |
| 403 | `forbidden` (ambiguous/unsupported role or absent exact grant) |
| 503 | `state_unavailable` (clock regression or unavailable query configuration) |
| 500 | `internal_error` (unexpected failure, with no raw exception body) |

Unknown routes return a fixed `not_found` error and unsupported methods return
`method_not_allowed`. Authentication precedes query diagnostics; authorization
precedes resource/filter diagnostics. Duplicate/missing home selectors fail
400 after authentication because there is no unique scope to authorize.
All responses, including errors and docs, set `Cache-Control: no-store` and
`X-Content-Type-Options: nosniff`. The app exports no cookies and trusts no
identity override headers. GET bodies are rejected without accumulating them.

## Verification and rollback

```sh
ruff check apps/home-intelligence-api
mypy --config-file apps/home-intelligence-api/pyproject.toml apps/home-intelligence-api/src
python -m pytest -c apps/home-intelligence-api/pytest.ini apps/home-intelligence-api/tests -q --junitxml=/tmp/home-api-results.xml
python apps/home-intelligence-api/tests/build_artifacts.py --out-dir /tmp/home-api-artifacts --test-results /tmp/home-api-results.xml
```

Imports and skipped acceptance tests fail the required suite. The artifact
runner builds direct wheels and sdists for API/fabric/shared contracts, rebuilds
wheels from each sdist, downloads dependencies once, and installs each triplet
in a clean environment offline. Normal and optimized isolated Python run the
same real JWT/HTTP smoke and must produce identical OpenAPI digests. Provenance
records source hashes, artifact hashes, interpreter and required test results.
CI executes Python 3.12/3.13/3.14 with dependency-sensitive path triggers.

No database migration or live deployment is part of this increment. Rollback
means removing the app from composition or reverting this package version;
there are no physical effects or persisted task mutations to reverse. Key/grant
changes require rolling back trusted configuration deliberately, not retaining
a revoked key or caller grant through an old app instance.
