# Architecture

## Overview

SaaSGuard-Lite keeps a simple multi-service shape:

- Frontend service handles login, active-tenant selection, export initiation, job inspection, and OE navigation.
- API service handles authentication, application authorization, job creation, audit writes, and API metrics.
- Worker service handles asynchronous export execution and worker metrics.
- PostgreSQL is the source of truth for users, tenants, memberships, jobs, and audit evidence.
- Redis is the queue transport only.
- MinIO stores completed CSV exports. Browser downloads still flow through the API so tenant authorization is enforced at read time.
- Keycloak issues OIDC bearer tokens for local development.
- Prometheus scrapes metrics.
- Loki stores logs shipped by Promtail.
- Grafana provides starter dashboards.

## Authentication and authorization split

- The React frontend uses Keycloak PKCE for browser login and does not expose raw tokens in the UI.
- Keycloak is responsible only for proving identity.
- The FastAPI application validates issuer, audience, signature, and expiration against Keycloak JWKS.
- The application maps token `sub` to internal `users.keycloak_sub`.
- Tenant authorization is resolved from `memberships`, not from token roles.
- Internal global operations access is resolved from the application `users.internal_role`, not from frontend-only checks.
- Multi-tenant users select an active tenant with `X-Active-Tenant`.

## Authoritative data path

Application-level tenant controls live in PostgreSQL:

- `users` defines the internal user registry.
- `tenants` defines active tenants.
- `memberships` defines role bindings.
- `export_jobs` stores the authoritative async context and state machine.
- `audit_events` stores durable evidence.

## Async trust boundary

Queue payloads are intentionally minimal:

- Redis message body: `job_id`

The worker flow is:

1. Receive `job_id`.
2. Load the job from PostgreSQL.
3. Atomically claim the job only if it is runnable.
4. Reconstruct trusted tenant context from the job record already written by the API.
5. Run tenant-scoped queries using `tenant_id`.
6. Upload the result to MinIO.
7. Persist completion or failure state and write correlated logs and audit records.
8. Serve completed downloads back through `GET /jobs/{job_id}/download` after the API revalidates tenant membership and role access.

This prevents queue tampering from becoming an authorization source.

## Worker state model

`export_jobs.status` uses:

- `queued`
- `retry_pending`
- `processing`
- `completed`
- `failed`

Transient failures:

- increment `retry_count`
- retain stage-specific `failure_stage`
- requeue only up to the configured limit

Terminal failures:

- move to `failed`
- persist a bounded error message
- write an audit event

## Telemetry

### Logs

Application logs are JSON to stdout with correlation and entity fields. Promtail ships them to Loki.

### Metrics

Prometheus metrics include:

- API request count and latency
- auth failures
- authorization denials
- export requests created
- job read denials
- worker starts, completions, failures, retries
- job duration
- queue wait time
- DB query failures
- MinIO upload failures
- export row counts
- queue backlog
- oldest pending job age

Tenant labels are used only on bounded tenant metrics in this local stack and intentionally avoid per-user cardinality.

### Audit evidence

`audit_events` persists:

- export requested
- authorization denied
- job viewed
- export completed
- export failed
- export downloaded

## Migrations

The application uses idempotent SQL migrations in [sql/migrations](/home/darthdg/saasguard/sql/migrations). A lightweight migration runner applies them under a PostgreSQL advisory lock at service startup.
