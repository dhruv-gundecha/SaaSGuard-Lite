# Technical Design Document: SaaSGuard-Lite

---

## 1. Overview

SaaSGuard-Lite is a minimal multi-tenant SaaS simulation platform designed to demonstrate security failures in asynchronous data processing workflows.

The system models a simplified SaaS application where users belong to tenants (organizations), interact with tenant-scoped data, and can request data exports. Export processing is handled asynchronously via a background worker.

---

## 2. Purpose

The system is designed to support:

* security testing
* incident response simulation
* observability and detection analysis

Key focus areas:

* authentication vs authorization
* tenant isolation
* identity propagation across async systems
* logging for detection and investigation

The system specifically enables simulation of a failure scenario where:

* authorization is correctly enforced at the API layer
* but not enforced in the worker
* resulting in cross-tenant data exposure

---

## 3. System Architecture

Frontend (optional)
        ↓
       API
        ↓
    Postgres

API → Redis (queue) → Worker → MinIO

OIDC via Keycloak

Logs → Promtail → Loki → Grafana

---

## 4. Core Components

### API Service

* Validates user identity (OIDC or mocked)
* Maps user → tenant
* Enforces tenant-scoped access
* Exposes endpoints for records and exports
* Creates export jobs
* Emits audit logs

---

### Worker Service

* Consumes jobs from Redis
* Loads export metadata
* Queries records
* Generates CSV files
* Uploads to MinIO
* Updates export status

---

### Postgres

Stores:

* tenants
* users
* records
* exports
* audit_logs

---

### Redis

* Queue for export jobs
* Enables asynchronous processing

---

### MinIO

* Stores generated export files

---

### Keycloak

* OIDC identity provider
* Issues JWT tokens
* API maps `sub` → user → tenant

---

### Observability Stack

* Promtail (log collection)
* Loki (log storage)
* Grafana (visualization)

---

## 5. Technical Decisions and Tradeoffs

* **FastAPI (Python):** chosen for rapid development and simple API design; trades off deep production ecosystem features
* **Python Worker (custom loop):** minimal complexity and easy integration; lacks advanced queue management features
* **Postgres (shared schema):** simple multi-tenant model using `tenant_id`; requires strict query discipline
* **Redis (queue):** lightweight and easy to integrate; not as robust as full message brokers
* **MinIO:** local S3-compatible storage; simplified compared to managed cloud storage
* **Keycloak:** realistic OIDC provider; introduces setup overhead

---

## 6. Multi-Tenant Data Model

Tenant isolation is implemented using a shared database with a `tenant_id` field.

### Key Tables

* tenants
* users (`oidc_sub`, `tenant_id`)
* records (`tenant_id`)
* exports (`tenant_id`, `requested_by`)
* audit_logs

### Principle


All data access is scoped by tenant_id

---

## 7. Core Workflows

### View Records

* User requests records
* API resolves tenant
* Returns tenant-scoped data

---

### Request Export

* API creates export record
* Job is pushed to Redis
* Export ID returned

---

### Export Processing

* Worker retrieves job
* Queries records
* Generates CSV
* Uploads to MinIO
* Updates status

---

### Download Export

* API validates ownership
* Returns file from storage

---

## 8. Out of Scope

* Advanced RBAC or permission systems
* Complex frontend or UI features
* High scalability or distributed deployment
* Production-grade security hardening

---

## 9. Summary

SaaSGuard-Lite is a minimal multi-tenant system designed to demonstrate authorization failures in asynchronous workflows.

The architecture combines:

* tenant-scoped data
* async processing
* object storage
* identity integration

to support realistic security analysis and incident simulation.
