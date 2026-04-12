# Technical Design Document: SaaSGuard-Lite

---

## 1. Overview

SaaSGuard-Lite is a minimal multi-tenant SaaS simulation platform designed to model secure data access patterns and support security testing and incident response analysis.

The system represents a simplified SaaS application where users belong to tenants (organizations), interact with tenant-scoped data, and can request data exports. Export processing is handled asynchronously via a background worker.

---

## 2. Purpose

The system is designed to support:

- security testing
- threat modeling
- incident response simulation
- observability and detection analysis

Key focus areas include:

- authentication vs authorization
- tenant isolation
- identity propagation across asynchronous systems
- logging and auditability

The system is implemented with a secure-by-design approach and is used to analyze potential failure scenarios in asynchronous workflows.

---

## 3. System Architecture
Frontend (optional)
↓
API
↓
Postgres

API → Redis (queue) → Worker → MinIO

OIDC via Keycloak (optional)

Logs → Promtail → Loki → Grafana

---

## 4. Core Components

### API Service

- Handles incoming requests
- Validates user identity (OIDC or mocked)
- Maps user → tenant
- Enforces tenant-scoped access control
- Exposes endpoints for records and exports
- Creates export jobs
- Writes job metadata to PostgreSQL
- Emits audit logs

---

### Worker Service

- Consumes jobs from Redis queue
- Receives only job identifiers (job_id)
- Reloads job metadata from PostgreSQL (source of truth)
- Uses tenant context from stored job data
- Queries tenant-scoped records
- Generates CSV export files
- Uploads files to MinIO
- Updates export status

---

### PostgreSQL

Stores all authoritative application data:

- tenants
- users
- records
- exports
- audit_logs

Used as the source of truth for identity and authorization context.

---

### Redis

- Acts as a queue for export jobs
- Decouples API from worker
- Transports minimal data (job_id only)

---

### MinIO

- Stores generated export files
- Uses tenant-scoped object paths:
  `exports/<tenant_id>/<job_id>.csv`

---

### Keycloak (Optional)

- Provides OIDC-based authentication
- Issues JWT tokens
- API maps token (`sub`) → user → tenant

---

### Observability Stack (Optional)

- Promtail: log collection
- Loki: log storage
- Grafana: visualization

---

## 5. Technical Decisions and Tradeoffs

- **FastAPI (Python):** simple and fast to build; limited enterprise features
- **Celery + Redis:** easy async processing; less robust than full brokers
- **PostgreSQL:** central source of truth; requires strict tenant filtering
- **MinIO:** simple object storage; not production-grade cloud storage
- **Keycloak (optional):** realistic auth; adds setup complexity
- **Minimal queue payload:** improves security by reducing trust in message transport

---

## 6. Multi-Tenant Data Model

Tenant isolation is implemented using a shared database with a `tenant_id` field.

### Key Tables

- tenants
- users (`oidc_sub`, `tenant_id`)
- records (`tenant_id`)
- exports (`tenant_id`, `requested_by`)
- audit_logs

### Principle

All data access must be scoped using `tenant_id`.

---

## 7. Core Workflows

### View Records

- User sends request
- API validates identity
- API resolves tenant
- Returns only tenant-scoped records

---

### Request Export

- API validates user
- Determines tenant
- Creates export record in PostgreSQL
- Stores `tenant_id` and `requested_by`
- Sends only `job_id` to Redis
- Returns job ID to user

---

### Export Processing

- Worker receives `job_id`
- Reloads job from PostgreSQL
- Extracts `tenant_id`
- Queries records using tenant filter
- Generates CSV
- Stores file in MinIO
- Updates job status

---

### Download Export

- User requests export
- API validates identity
- API verifies export belongs to user's tenant
- Returns file or access link

---

## 8. Security Considerations

- Authorization is enforced using tenant-based filtering
- PostgreSQL is used as the source of truth for job context
- Queue messages do not contain sensitive data
- Worker does not trust external input and reloads state from database
- Object storage paths are tenant-scoped
- Logging is required for audit and investigation

---

## 9. Out of Scope

- Advanced RBAC systems
- Complex frontend UI
- Large-scale distributed systems
- Production-grade security hardening
- Full compliance implementation

---

## 10. Summary

SaaSGuard-Lite is a minimal multi-tenant system designed to model secure data access patterns in asynchronous workflows.

The system focuses on:

- tenant isolation
- correct authorization enforcement
- safe async processing
- traceability through logs

It provides a foundation for analyzing realistic security risks and testing incident response scenarios.