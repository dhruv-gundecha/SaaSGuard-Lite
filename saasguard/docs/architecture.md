# Architecture

## Overview

SaaSGuard-Lite is a multi-container demo platform built around tenant-scoped export processing and operational visibility. The backend implementation, Docker Compose stack, dashboards, and tests are the current source of truth.

## Service Layout

```text
Frontend (React + Vite)
  |
  +--> Keycloak for browser login (PKCE)
  |
  +--> FastAPI API
         |
         +--> PostgreSQL
         +--> Redis
         +--> MinIO
         +--> Prometheus /metrics
         +--> audit_events
         |
         +--> Celery queue message: job_id only
                    |
                    v
                Celery Worker
                    |
                    +--> PostgreSQL authoritative job + tenant records
                    +--> MinIO CSV object upload
                    +--> Prometheus worker metrics

Logs --> Promtail --> Loki --> Grafana
Metrics --> Prometheus --> Grafana
Availability checks --> Uptime Kuma
```

## Core Responsibilities

### Frontend

- handles browser sign-in through Keycloak
- loads `/me` to resolve memberships and operations access
- stores the active tenant in `sessionStorage`
- sends `X-Active-Tenant` for tenant-scoped requests
- exposes the internal-only `Operations` page only when the API session says operations access is allowed

### API

- validates bearer tokens against Keycloak JWKS
- resolves internal users and tenant memberships from PostgreSQL
- enforces tenant and internal-role authorization
- creates export jobs
- serves job views and secure CSV downloads
- records audit events
- exposes Prometheus metrics
- computes tenant and global operations summaries

### Worker

- receives only `job_id` from Redis/Celery
- reloads authoritative job and tenant context from PostgreSQL
- fetches tenant records
- generates CSV content
- uploads the result to MinIO
- records completion, retries, and failures
- exposes worker metrics

### Datastores and dependencies

- PostgreSQL: users, memberships, tenants, tenant_records, export_jobs, audit_events
- Redis: broker/transport only
- MinIO: export object storage
- Keycloak: OIDC identity provider

### Observability

- Prometheus scrapes API and worker metrics
- Promtail ships container logs to Loki
- Grafana provides provisioned dashboards
- Uptime Kuma provides separate service-health checks

## Application Roles

Tenant-scoped roles:

- `viewer`
- `analyst`
- `tenant_admin`

Internal roles:

- `soc_admin`
- `ops_admin`

Important distinction:

- Keycloak proves identity
- the application decides authorization from PostgreSQL memberships and `users.internal_role`

## Data Flows

### 1. Authentication flow

1. The browser starts Keycloak PKCE login.
2. Keycloak returns an access token.
3. The frontend sends the bearer token to the API.
4. The API validates issuer, audience, signature, expiration, and subject.
5. The API maps `sub` to an internal user record and loads memberships.

### 2. Export creation flow

1. A tenant user calls `POST /exports`.
2. The API resolves active tenant context.
3. The API checks that the role is at least `analyst`.
4. The API creates an `export_jobs` row in PostgreSQL.
5. The API enqueues only the string form of `job_id`.
6. The API records audit evidence and metrics.

### 3. Worker processing flow

1. The worker receives `job_id`.
2. The worker loads the job from PostgreSQL.
3. The worker claims the job only if it is runnable.
4. The worker reloads trusted tenant context from the job record.
5. The worker queries tenant records from PostgreSQL.
6. The worker writes a CSV to MinIO.
7. The worker updates job state and emits audit/log/metric evidence.

### 4. Export download flow

1. A tenant user calls `GET /jobs/{job_id}/download`.
2. The API looks up the job.
3. The API checks that the user has membership in the job’s tenant.
4. The API checks role `viewer` or higher.
5. The API requires the job to be `completed` with a non-null object key.
6. The API downloads the object from MinIO and streams it back as CSV.

### 5. Operations flow

1. The frontend requests `/operations/summary` only for sessions with internal operations access.
2. The backend enforces `soc_admin` or `ops_admin`.
3. The summary combines:
   - bounded dependency checks
   - in-memory API traffic observations
   - PostgreSQL export state
   - worker metric totals
4. The frontend links operators to Grafana, Prometheus, Loki, Uptime Kuma, and MinIO.

## Trust Boundaries

### Browser boundary

- the browser is untrusted
- tenant selection from the browser is validated against memberships

### Identity boundary

- Keycloak proves identity only
- application authorization is separate

### Queue boundary

- Redis is not trusted to carry tenant context
- only `job_id` crosses the queue boundary

### Storage boundary

- MinIO stores objects but does not replace application authorization
- the API remains the download gate

### Observability boundary

- Grafana, Loki, Prometheus, and Uptime Kuma may expose cross-tenant operational context
- access is therefore more sensitive than tenant-scoped product views

## Current Operational Signals

The current implementation exposes metrics and logs for:

- API request counts and latency
- authentication failures
- authorization denials
- job-read denials
- export request creation
- worker starts, completions, failures, retries
- MinIO upload failures
- database query failures
- queue backlog
- oldest pending job age
- stale processing jobs

## Known Limitations

- the frontend container currently runs a development server instead of a production static-serving path
- the current test suite is strongest on backend behavior and lighter on browser-based auth flows
- the local stack includes demo credentials and admin surfaces appropriate for coursework, not production
