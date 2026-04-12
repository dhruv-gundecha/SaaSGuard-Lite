# Threat Model: SaaSGuard-Lite

## Step 1: Scope the System

### System Overview

The system is a containerized export service with the following components:

- FastAPI API
- PostgreSQL database
- Redis queue
- Celery worker
- MinIO object storage

Data flow:

User → API → PostgreSQL (job stored) → Redis (job_id) → Worker → PostgreSQL (reload job) → MinIO (CSV stored)

---

### Entry Points

- `POST /exports`
- `GET /jobs/{job_id}`
- `X-User` header
- MinIO service (if exposed)

---

### Assets

- Tenant data in PostgreSQL
- Export job records
- Generated CSV files
- User to tenant mapping
- Environment variables (.env)

---

### Trust Boundaries

- User → API (untrusted to trusted)
- API → Redis (trusted to untrusted transport)
- Redis → Worker (must re-establish trust)
- Worker → MinIO (data leaves system)

---

### Threat Actors

- Malicious user
- Unauthenticated attacker
- Insider user
- Misconfigured services

---

### User Story

A user requests an export of their tenant data and receives a CSV file containing only their data.

---

### Abuse Case

A user attempts to access or export another tenant’s data.

---

## Step 2: Determine Threats (STRIDE)

### Spoofing

- User sets `X-User` to another user
- No real authentication

---

### Tampering

- Accessing other users’ job IDs
- Modifying requests to access unauthorized data

---

### Repudiation

- No logging of user actions
- No way to track who accessed or created exports

---

### Information Disclosure

- Cross-tenant data exposure if filtering fails
- Accessing other tenant export files
- Guessing object paths in MinIO

---

### Denial of Service

- Repeated export requests
- Large dataset exports
- Worker overload

---

### Elevation of Privilege

- User impersonates another user via header
- Accesses jobs across tenants

---

## Step 3: Countermeasures and Mitigation

### Existing Controls

- Job stored in PostgreSQL before processing
- Only `job_id` sent through queue
- Worker reloads job from database
- Tenant ID stored with job
- Queries filtered by tenant
- Object keys include tenant

---

### Risks and Mitigations

#### Weak Authentication
- Risk: `X-User` is not secure
- Mitigation: Use JWT or OIDC

---

#### Unauthorized Job Access
- Risk: Accessing jobs across tenants
- Mitigation: Check tenant_id when fetching jobs

---

#### Missing Logging
- Risk: No audit trail
- Mitigation: Add logging for actions

---

#### Object Storage Access
- Risk: Accessing other tenant files
- Mitigation: Use signed URLs and restrict access

---

#### Denial of Service
- Risk: Too many export requests
- Mitigation: Add rate limiting

---

### Risk Handling

- Accept: simple authentication for demo
- Mitigate: tenant filtering and DB-based context
- Improve: add authentication and logging later