# Security Test Documentation: SaaSGuard-Lite

## Objectives

- validate OIDC bearer token authentication
- enforce application-level tenant authorization
- confirm the queue carries only `job_id`
- confirm the worker reconstructs trusted context from PostgreSQL
- verify tenant-scoped exports and job access
- verify audit and telemetry evidence for key actions

## Test environment

- Docker Compose stack from this repository
- API at `http://localhost:8000`
- Keycloak at `http://localhost:8080`
- Prometheus at `http://localhost:9090`
- Grafana at `http://localhost:3000`

## Seeded users

- `alice` in `tenant_alpha`
- `bob` in `tenant_beta`
- `carol` in both tenants as `tenant_admin`

## Authentication tests

1. Valid token
   Expected: `POST /exports` succeeds for `alice`
2. Missing bearer token
   Expected: `401`
3. Invalid bearer token
   Expected: `401` and `auth.token_rejected` log event
4. Expired token
   Expected: `401`

## Authorization tests

1. Active tenant required for multi-tenant user
   Expected: `carol` without `X-Active-Tenant` receives `400`
2. Create export requires `analyst` or `tenant_admin`
   Expected: lower roles are denied with audit evidence
3. Cross-tenant job access
   Expected: `bob` cannot read `alice` job and receives `403`
4. Cross-tenant download access
   Expected: `bob` cannot download `alice` export
5. Audit endpoint restricted to `tenant_admin`
   Expected: non-admins receive `403`

## Async authorization tests

1. Queue payload inspection
   Expected: message contains only `job_id`
2. Worker database reload
   Expected: worker logs `worker.job_loaded` and `worker.context_resolved`
3. Tenant data isolation
   Expected: CSV contains only rows for the authoritative `tenant_id`
4. Duplicate delivery safety
   Expected: second worker attempt skips a non-runnable job
5. Retry behavior
   Expected: transient dependency failures retry only up to the configured limit

## Observability tests

1. Correlation ID propagation
   Expected: API and worker logs share the same `correlation_id`
2. Metrics exposure
   Expected: `/metrics` and worker metrics endpoint expose scrapeable counters and histograms
3. Audit evidence
   Expected: `audit_events` contains export requested, job viewed, denied actions, and job completion or failure

## Negative tests

1. Invalid job ID format
   Expected: request rejected by FastAPI validation
2. Unknown provisioned user
   Expected: valid token with unmapped `sub` receives `403`
3. MinIO outage
   Expected: upload failures are retried, then job moves to `failed`
