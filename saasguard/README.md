# SaaSGuard-Lite

## Project Overview

SaaSGuard-Lite is a mock multi-tenant SaaS platform used to demonstrate secure-by-design architecture, tenant-scoped authorization, asynchronous export processing, operational monitoring, and incident preparedness.

The repository centers on a realistic export workflow:

- users authenticate through Keycloak
- the API validates OIDC tokens and resolves application roles from PostgreSQL
- authorized users create export jobs for an active tenant
- Redis carries only the job identifier
- a Celery worker reloads authoritative job context from PostgreSQL and writes CSVs to MinIO
- completed exports are downloaded through the API after authorization is re-checked
- Prometheus, Loki, Grafana, and Uptime Kuma provide OE visibility

## Architecture

```text
Browser UI (React + Vite)
        |
        | OIDC login / bearer token
        v
    Keycloak ------------------------------+
                                           |
                                           v
FastAPI API  <-----> PostgreSQL <-----> Audit Events
    |  ^              |
    |  |              +---- memberships / users / export_jobs / tenant_records
    |  |
    |  +---- secure CSV download
    |
    +---- enqueue job_id only ----> Redis ----> Celery Worker
                                              |
                                              +---- reload authoritative job + tenant context from PostgreSQL
                                              +---- generate CSV
                                              +---- upload to MinIO

Observability:
API /metrics --------\
Worker /metrics -----+--> Prometheus --> Grafana
Container logs ------> Promtail --> Loki --> Grafana
Edge / dependency checks -------------> Uptime Kuma
```

More detail: [Architecture](saasguard/docs/architecture.md)

## Key Features

- Authentication: Keycloak-backed OIDC with bearer-token validation in the API
- Authorization: tenant-scoped roles (`viewer`, `analyst`, `tenant_admin`) plus internal operations roles (`soc_admin`, `ops_admin`)
- Tenant isolation: authorization resolved from PostgreSQL memberships, not from browser state alone
- Export workflow: `POST /exports` creates a queued job and the worker processes it asynchronously
- Secure export download: completed exports are served through the API, not by direct MinIO browser access
- Audit logging: application security events are written to PostgreSQL `audit_events`
- Operational monitoring: dashboard-style OE visibility through Grafana, Prometheus, Loki, and Uptime Kuma
- Internal operations command center: `/operations/summary` and the frontend `Operations` page are restricted to internal roles

## Technology Stack

- Backend: FastAPI, PyJWT, Psycopg, Celery, Redis client, Boto3
- Frontend: React, React Router, Vite, TypeScript, Keycloak JS
- Datastores and dependencies: PostgreSQL, Redis, MinIO, Keycloak
- Observability: Prometheus, Loki, Promtail, Grafana, Uptime Kuma
- Packaging and runtime: Docker, Docker Compose
- CI: GitHub Actions

## Docker Setup

Primary stack definition: [Docker Compose](saasguard/docker-compose.yml)

Services defined in the current stack:

- `api`
- `frontend`
- `worker`
- `postgres`
- `redis`
- `minio`
- `keycloak`
- `prometheus`
- `loki`
- `promtail`
- `grafana`
- `uptime-kuma`

## Running the Project

1. Create local environment files from the committed templates:

```bash
cp .env.example .env
cp frontend/.env.example frontend/.env
```

2. Add the local Keycloak hostname:

```text
127.0.0.1 auth.saasguard.local
```

3. Start the stack:

```bash
docker compose up --build
```

4. Optional clean reset:

```bash
docker compose down -v
docker compose up --build
```

Local endpoints:

- API: `http://localhost:8000`
- Frontend: `http://localhost:3001`
- Keycloak: `http://auth.saasguard.local:8081`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`
- Loki via Grafana Explore: `http://localhost:3000/explore`
- Uptime Kuma: `http://localhost:3002`
- MinIO API: `http://localhost:9000`
- MinIO console: `http://localhost:9001`
- Worker metrics: `http://localhost:9101`

## Seeded Demo Users

The current Keycloak realm import and seed data define:

- `alice` / `alice-password` -> `tenant_alpha` -> `analyst`
- `bob` / `bob-password` -> `tenant_beta` -> `analyst`
- `carol` / `carol-password` -> `tenant_alpha`, `tenant_beta` -> `tenant_admin`
- `soc` / `soc-password` -> internal `soc_admin`

Local-only note:

- the backend can repair seeded internal identity mappings by username when `DEV_AUTH_USERNAME_FALLBACK_ENABLED=true`
- that behavior exists for local/demo stability and is not a production hardening pattern

## CI/CD Pipeline

Workflow file: [GitHub Actions Workflow](.github/workflows/tests.yml)

Current checked-in workflow behavior:

- checks out the repository
- runs from the `saasguard/` project directory under the repository root
- sets up Docker Buildx
- creates backend `.env` from `.env.example`
- creates frontend `.env` from `frontend/.env.example`
- runs `docker compose config`
- runs `docker compose up -d --build`
- runs `docker compose ps`
- runs `docker compose run --rm -v "$PWD:/app" api pytest -v`
- runs `docker compose exec frontend npm run build`
- tears the stack down on completion

Local validation in this workspace still confirmed that:

- `docker compose config` succeeds
- the Docker stack boots successfully
- backend pytest passes
- `docker compose exec frontend npm run build` succeeds

## OE Dashboard

SaaSGuard-Lite includes:

- a frontend `Operations` page for internal operators
- provisioned Grafana dashboards
- Prometheus metrics from the API and worker
- Loki log aggregation
- Uptime Kuma dependency and edge health visibility

Provisioned Grafana dashboards:

- `Service Health`
- `Tenant Impact`
- `Auth and Security`

Current implementation highlights:

- the Operations page is visible only when `session.authorization.can_access_operations` is true
- backend access to `/operations/summary` is limited to `soc_admin` and `ops_admin`
- the Operations page links to Grafana, Prometheus, Loki, Uptime Kuma, and the MinIO console

Dashboard evidence: [OE Dashboard Verification](saasguard/docs/oe-dashboard-verification.md)

## Operational Alerts

Grafana dashboards in this repository are used for investigation. Grafana alert rules are used for detection so operators do not need to continuously watch dashboards.

Current alert provisioning lives under:

- [Grafana Alert Provisioning](saasguard/observability/grafana/provisioning/alerting)

Current local-demo alert coverage includes:

- authentication failure spike
- authorization denial spike
- export failure spike
- queue backlog growth
- worker failure or retry spike
- MinIO upload failure spike

Local demo note:

- the repository provisions a placeholder local-demo contact point without real Slack, email, or PagerDuty secrets
- in local development, alerts can be viewed directly in the Grafana Alerting UI
- a production deployment would route alerts to Slack, PagerDuty, email, or another on-call destination

## Security Controls

- OIDC issuer, audience, signature, and expiration validation in `src/auth.py`
- PostgreSQL-backed tenant membership and internal-role authorization in `src/authz.py`
- explicit `X-Active-Tenant` handling for multi-tenant users
- queue payload minimized to `job_id` only
- worker reloads trusted job state and tenant context from PostgreSQL
- completed export download authorization is enforced again at read time
- JSON logging avoids raw JWTs, passwords, and CSV contents
- audit events capture export requests, denials, job views, failures, completions, and downloads
- API security headers are added on responses
- in-memory rate limiting exists for export creation

## Threat Model

Threat model: [Threat Model](saasguard/docs/threat-model.md)

Key modeled threats include:

- cross-tenant data exposure
- authorization bypass
- OIDC issuer/audience validation failures
- Keycloak dependency failures
- Redis queue tampering
- MinIO exposure
- worker failures and queue backlog growth
- logging and observability leakage
- operational dashboard access risks

## Security Testing

Security testing matrix: [Security Testing](saasguard/security_tests.md)

Current automated backend coverage includes:

- export creation authorization
- cross-tenant job-read denial
- secure export download behavior
- queue trust-boundary behavior
- auth failure metrics
- operations access control
- tenant-scoped dashboard summary behavior
- required OE metrics exposure

Documented but not yet automated at the same depth:

- browser-based PKCE flow
- frontend download regression
- live Keycloak token-acquisition and discovery/JWKS integration coverage in CI

## Compliance

Compliance mapping documents:

- [Compliance Requirements](saasguard/docs/compliance-requirements.md)
- [Compliance Audit](saasguard/docs/compliance-audit.md)
- [Non-Compliance Consequences](saasguard/docs/non-compliance-consequences.md)

These documents map the current implementation to relevant control expectations such as SOC 2, CIS Controls, and OWASP guidance. They do not claim formal certification.

## Incident Response

Incident runbook: [Incident Runbook](saasguard/docs/incident-runbook.md)

Current documented incident classes include:

- token validation failure spike
- OIDC issuer mismatch
- authorization denial spike
- MinIO outage
- queue backlog growth
- worker failure spike

## Simulated Incident

Simulation walkthrough: [Incident Simulation](saasguard/docs/incident-simulation.md)

The current documented scenario is an OIDC issuer mismatch in the API configuration. It uses Grafana, Loki, and Uptime Kuma as the main detection surfaces and validates recovery by restoring authentication, tenant context, and successful export workflows.

Recording: [incident-video.mp4](saasguard/incident-video.mp4)

## Repository Structure

```text
saasguard/
  api/                  Dockerfile for FastAPI service
  worker/               Dockerfile for Celery worker
  frontend/             React + Vite application
  src/                  backend application code
  tests/                backend automated tests
  observability/        Prometheus, Grafana, Loki, Promtail config
  keycloak/             realm import for local OIDC
  docs/                 architecture, OE, compliance, incident docs
  docker-compose.yml    local multi-service stack
  security_tests.md     security testing matrix
.github/workflows/      GitHub Actions workflow at repository root
```

## Final Submission Artifacts

- Docker Compose: [Docker Compose](saasguard/docker-compose.yml)
- CI/CD workflow: [GitHub Actions Workflow](.github/workflows/tests.yml)
- OE dashboard verification: [OE Dashboard Verification](saasguard/docs/oe-dashboard-verification.md)
- Threat model: [Threat Model](saasguard/docs/threat-model.md)
- Security testing: [Security Testing](saasguard/security_tests.md)
- Compliance requirements: [Compliance Requirements](saasguard/docs/compliance-requirements.md)
- Compliance audit: [Compliance Audit](saasguard/docs/compliance-audit.md)
- Non-compliance consequences: [Non-Compliance Consequences](saasguard/docs/non-compliance-consequences.md)
- Incident runbook: [Incident Runbook](saasguard/docs/incident-runbook.md)
- Incident simulation: [Incident Simulation](saasguard/docs/incident-simulation.md)
- Incident recording: [incident-video.mp4](saasguard/incident-video.mp4)
- Final readiness report: [Final Readiness Report](saasguard/docs/final-deliverables-readiness.md)
