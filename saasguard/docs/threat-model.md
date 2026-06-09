# Threat Model

This threat model is derived from the current implementation in `src/`, `frontend/`, `tests/`, `docker-compose.yml`, and the current observability configuration.

## Architecture Overview

SaaSGuard-Lite is a multi-tenant export platform with:

- Keycloak for identity
- FastAPI for token validation, tenant authorization, audit logging, and download control
- PostgreSQL for users, memberships, export jobs, tenant records, and audit events
- Redis as queue transport only
- Celery worker for export generation
- MinIO for object storage
- React frontend for tenant and operations views
- Prometheus, Loki, Grafana, and Uptime Kuma for OE visibility

## Data Flows

### Authentication flow

1. The browser authenticates with Keycloak using PKCE.
2. The frontend sends the bearer token to the API.
3. The API validates issuer, audience, signature, expiration, and subject.
4. The API resolves the internal user and memberships from PostgreSQL.

### Export request flow

1. The frontend calls `POST /exports`.
2. The API resolves the active tenant and required role.
3. The API creates an `export_jobs` row in PostgreSQL.
4. The API enqueues only `job_id`.

### Worker flow

1. The worker receives `job_id`.
2. The worker reloads the job from PostgreSQL.
3. The worker fetches tenant records from PostgreSQL.
4. The worker uploads the CSV to MinIO.
5. The worker updates job state and audit evidence.

### Download flow

1. The user calls `GET /jobs/{job_id}/download`.
2. The API verifies membership in the job’s tenant.
3. The API checks role and completed state.
4. The API downloads from MinIO and streams the CSV to the caller.

## Trust Boundaries

### Browser boundary

- untrusted client
- tenant context from the browser must be re-validated by the API

### Identity boundary

- Keycloak proves identity
- application authorization remains separate

### Queue boundary

- Redis is not trusted with tenant or role context
- only `job_id` is allowed to cross the queue boundary

### Storage boundary

- MinIO stores artifacts
- it must not become a direct authorization bypass

### Observability boundary

- Grafana, Loki, Prometheus, Uptime Kuma, and the Operations page can expose global platform state
- these surfaces are more sensitive than tenant-scoped user views

## Threat Inventory

| Threat | Priority | Why it matters | Current mitigations | Residual risk |
| --- | --- | --- | --- | --- |
| Cross-tenant data exposure | High | platform-boundary failure between tenants | tenant-scoped job reads, secure API download path, worker reloads authoritative context | no database-native row-level isolation demonstrated |
| Authorization bypass | High | unauthorized tenant or operations access | backend role checks, membership resolution from PostgreSQL, internal-role checks for operations | browser E2E regression coverage is limited |
| OIDC issuer validation failure | High | valid users rejected or wrong-issuer tokens mishandled | strict issuer validation, logs, metrics, runbook, simulation, and deterministic OIDC tests in `tests/test_oidc_authentication.py` | no live identity-provider integration test in CI yet |
| OIDC audience validation failure | High | wrong-client tokens may be mishandled | strict audience validation in API plus deterministic OIDC tests in `tests/test_oidc_authentication.py` | no live identity-provider integration test in CI yet |
| Keycloak dependency failure | High | users cannot obtain or validate working sessions | dependency checks, runbook guidance, Uptime Kuma, Grafana/Loki investigation path | failure drills are not fully automated |
| Redis queue tampering | High | worker could trust untrusted queue context | queue contains only `job_id`, worker reloads job from PostgreSQL | broker integrity beyond minimal-payload design is not deeply modeled |
| MinIO exposure | Medium | direct object path or admin misuse could weaken data protection | API-mediated downloads, worker metrics, runbook coverage | local admin surfaces still exist for demo use |
| Worker failure | Medium | queued jobs do not complete | retries, failure stages, metrics, logs, runbook | no full chaos-style automated drill |
| Queue backlog growth | Medium | customer-visible report delay | queue age/backlog metrics, operations summary, dashboards, and committed Grafana alert rules | local/demo thresholds still need production tuning |
| Logging and observability leakage | Medium | sensitive operational context may be overexposed | structured logs avoid raw secrets, operations page is internal-only | external observability access governance remains a residual risk |
| Operational dashboard access risk | Medium | tenant users could gain broad platform visibility | backend and frontend restrict operations access | needs hardened control beyond app-layer routing in real environments |

## Mitigations

- strict JWT validation in `src/auth.py`
- tenant and internal-role authorization in `src/authz.py`
- authoritative export-job state in PostgreSQL
- queue payload minimized to `job_id`
- secure API download path in `src/api.py`
- audit-event recording in API and worker code paths
- Prometheus metrics for auth, queue, worker, and dependency signals
- provisioned Grafana dashboards
- internal-only operations view

## Residual Risks

Fixed since earlier audit:

- deterministic OIDC authentication-path tests now cover issuer, audience, expiration, signature, subject, and issuer-contract mismatch in `tests/test_oidc_authentication.py`
- Grafana alert rules are now committed under `observability/grafana/provisioning/alerting/`

Still true:

- the current GitHub Actions workflow still needs root-path correction, `.env` bootstrapping, and frontend-build validation
- demo credentials and local admin surfaces are intentionally present for coursework
- observability-tool access control outside the application is only partially represented in repo evidence

Future production hardening:

- add one live identity-provider integration test in CI on top of the deterministic JWT-path tests
- tune local/demo alert thresholds for production operating conditions

## Threat Prioritization

Highest-priority threats for final submission discussion:

1. cross-tenant data exposure
2. authorization bypass
3. OIDC issuer or audience validation failure
4. Keycloak dependency failure
5. queue tampering across the worker trust boundary

Second-tier but still important:

1. MinIO exposure
2. worker failure
3. queue backlog growth
4. logging and observability leakage
5. operational dashboard access misuse
