# Threat Model: SaaSGuard-Lite

## Step 1: Scope the System

### System Overview

The system is a containerized secure multi-tenant export service with the following components:

- React + Vite frontend
- Keycloak for OIDC authentication
- FastAPI API
- PostgreSQL database
- Redis queue
- Celery worker
- MinIO object storage
- Prometheus, Loki, Promtail, Grafana, and Uptime Kuma for observability

Data flow:

User → Frontend → Keycloak login → API validates JWT → PostgreSQL authorization lookup → PostgreSQL job stored → Redis receives only `job_id` → Worker reloads job from PostgreSQL → Worker queries tenant-scoped data → MinIO stores CSV → API authorizes download

---

### Entry Points

- Frontend login through Keycloak
- `POST /exports`
- `GET /jobs/{job_id}`
- `GET /jobs/{job_id}/download`
- `GET /audit-events`
- `GET /operations/summary`
- `X-Active-Tenant` header
- Keycloak token endpoint
- MinIO service
- Prometheus `/metrics` endpoints
- Grafana dashboard
- Uptime Kuma monitors

---

### Assets

- Tenant data in PostgreSQL
- Internal users table
- Tenant membership and role mappings
- Export job records
- Generated CSV files in MinIO
- Keycloak bearer tokens
- Audit events
- Application logs
- Prometheus metrics
- Environment variables and service secrets

---

### Trust Boundaries

- Browser/frontend → API
- Browser/frontend → Keycloak
- API → Keycloak JWKS validation
- API → PostgreSQL
- API → Redis queue
- Redis → Worker
- Worker → PostgreSQL
- Worker → MinIO
- Application logs → Promtail → Loki
- Metrics endpoints → Prometheus → Grafana

Important trust boundary:

Redis is treated only as a transport queue. It carries only `job_id`. The worker must reload trusted tenant and job context from PostgreSQL before doing work.

---

### Threat Actors

- Unauthenticated attacker
- Authenticated user from one tenant
- Malicious tenant user
- Insider user with valid access
- Compromised frontend session
- Misconfigured service or deployment
- Attacker with access to Redis, MinIO, logs, or metrics
- Operator mistake during local development

---

### User Story

A user logs in through Keycloak, selects an authorized tenant, requests an export, and receives a CSV file containing only data for that tenant.

---

### Abuse Case

A user attempts to access, create, download, or inspect export jobs for a tenant they do not belong to.

---

## Step 2: Determine Threats (STRIDE)

### Spoofing

- Attacker uses a missing, expired, or forged bearer token
- Attacker tries to use a JWT from the wrong issuer or audience
- Attacker attempts to spoof another user by modifying frontend state
- Attacker tries to select another tenant using `X-Active-Tenant`
- Local development fallback could incorrectly map a Keycloak username to the wrong internal user if misused outside local mode

---

### Tampering

- Attacker modifies API requests to access another tenant
- Attacker tampers with `job_id` values in requests
- Attacker tampers with Redis queue messages
- Attacker attempts to modify job state directly
- Attacker attempts to alter MinIO object paths
- Misconfigured service writes incorrect job or tenant context

---

### Repudiation

- User denies requesting an export
- User denies downloading a completed export
- User denies attempting unauthorized tenant access
- Worker failure is difficult to trace without correlation IDs
- Operator cannot determine whether a failed export came from DB, worker, queue, or MinIO without logs and audit events

---

### Information Disclosure

- Cross-tenant data exposure if tenant filtering fails
- User accesses another tenant’s job metadata
- User downloads another tenant’s CSV export
- MinIO object keys reveal tenant or export information
- Logs accidentally expose tokens, secrets, passwords, or CSV contents
- Metrics expose excessive tenant/user-level labels
- Grafana, Prometheus, Loki, or Uptime Kuma exposed without proper access controls

---

### Denial of Service

- User repeatedly creates export jobs
- Large exports consume worker memory or CPU
- Redis queue backlog grows
- Worker gets stuck processing long jobs
- MinIO upload failures cause repeated retries
- PostgreSQL becomes overloaded by export queries
- Metrics/logging volume becomes too large
- Keycloak outage prevents login or token refresh

---

### Elevation of Privilege

- Viewer attempts analyst-only export creation
- Analyst attempts tenant-admin-only audit access
- User changes `X-Active-Tenant` to access another tenant
- Compromised token is used to perform actions as another user
- Worker trusts queue data instead of PostgreSQL
- Misconfigured Keycloak claims are treated as app authorization
- Direct database manipulation grants unauthorized membership or role

---

## Step 3: Countermeasures and Mitigation

### Existing Controls

- Keycloak handles authentication using OIDC bearer tokens
- React frontend uses PKCE for browser login
- API validates JWT issuer, audience, signature, expiration, and required claims
- API maps Keycloak `sub` to internal `users.keycloak_sub`
- Tenant authorization is resolved from PostgreSQL `memberships`, not token roles
- Multi-tenant users must select an active tenant using `X-Active-Tenant`
- Backend verifies the selected tenant against the user’s active memberships
- Roles are enforced in application code
- Job records are stored in PostgreSQL before async processing
- Redis carries only `job_id`
- Worker reloads trusted job and tenant context from PostgreSQL
- Worker queries tenant data using the stored `tenant_id`
- Worker atomically claims runnable jobs
- Job states include `queued`, `retry_pending`, `processing`, `completed`, and `failed`
- MinIO stores completed CSV exports
- Audit events are written for security-relevant actions
- Logs are structured JSON and avoid secrets, raw JWTs, passwords, and CSV contents
- Prometheus scrapes API and worker metrics
- Loki stores logs shipped by Promtail
- Grafana provides operational dashboards
- Uptime Kuma provides basic availability monitoring

---

### Risks and Mitigations

#### Broken Authentication
- Risk: Invalid or forged tokens are accepted
- Mitigation: Strict JWT validation using Keycloak JWKS, issuer, audience, signature, expiration, and required claims

---

#### Incorrect User Provisioning
- Risk: Valid Keycloak user has no correct internal user mapping
- Mitigation: Require matching internal `users.keycloak_sub`; keep username fallback limited to local development only

---

#### Unauthorized Tenant Access
- Risk: User selects another tenant through `X-Active-Tenant`
- Mitigation: Resolve active tenant only from the user’s active memberships in PostgreSQL

---

#### Unauthorized Role Access
- Risk: Viewer performs analyst or tenant-admin actions
- Mitigation: Enforce role hierarchy in backend authorization logic

---

#### Queue Tampering
- Risk: Redis message is modified to include attacker-controlled tenant or user context
- Mitigation: Queue carries only `job_id`; worker reloads tenant and requester context from PostgreSQL

---

#### Cross-Tenant Export
- Risk: Worker exports data for the wrong tenant
- Mitigation: Worker uses `tenant_id` stored in the authoritative job record and tenant-scoped SQL queries

---

#### Unauthorized Job Read or Download
- Risk: User guesses another tenant’s `job_id`
- Mitigation: Fetch jobs using both `job_id` and authorized `tenant_id`

---

#### Object Storage Exposure
- Risk: User accesses another tenant’s CSV directly from MinIO
- Mitigation: Keep MinIO behind backend-controlled access; authorize downloads through API; avoid public buckets

---

#### Missing Auditability
- Risk: Security-relevant actions cannot be investigated
- Mitigation: Write audit events for export requested, authorization denied, job viewed, export completed, export failed, and export downloaded

---

#### Sensitive Logging
- Risk: Logs expose secrets, tokens, or CSV contents
- Mitigation: Use structured logs and explicitly avoid raw JWTs, passwords, secrets, and CSV data

---

#### Observability Exposure
- Risk: Grafana, Prometheus, Loki, or Uptime Kuma reveal operational or tenant information
- Mitigation: Restrict access to observability tools; avoid high-cardinality per-user metrics; use bounded tenant labels only where appropriate

---

#### Denial of Service
- Risk: Repeated or large export requests overload API, database, queue, worker, or MinIO
- Mitigation: Add rate limiting, export size limits, job quotas, worker concurrency controls, retry limits, and backlog alerts

---

#### Dependency Outage
- Risk: Keycloak, PostgreSQL, Redis, MinIO, or worker outage breaks the export flow
- Mitigation: Use health checks, Uptime Kuma monitors, Prometheus metrics, Grafana dashboards, and incident runbooks

---

### Risk Handling

- Mitigate: cross-tenant access through DB-backed tenant authorization
- Mitigate: async trust risks by sending only `job_id` through Redis
- Mitigate: spoofing through Keycloak OIDC and JWT validation
- Mitigate: repudiation through durable audit events and structured logs
- Mitigate: operational failures through Prometheus, Loki, Grafana, and Uptime Kuma
- Accept: local development uses seeded users and development-only fallback behavior
- Improve: add production-grade signup/provisioning workflow
- Improve: add rate limiting and export quotas
- Improve: restrict MinIO access further with signed URLs or backend-only download flow
- Improve: strengthen observability access controls
- Improve: add alerting for authorization denial spikes, queue backlog, worker failures, and MinIO upload failures