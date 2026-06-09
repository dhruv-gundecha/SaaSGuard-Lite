# Compliance Requirements Mapping

This document maps the current SaaSGuard-Lite implementation to realistic control expectations. It does not claim formal compliance certification. It is a repository-grounded mapping for academic review.

## Relevant Frameworks

- SOC 2 Trust Services Criteria
- CIS Controls v8
- OWASP ASVS
- OWASP Top 10

## Scope

Current in-scope implementation areas:

- Keycloak OIDC authentication
- PostgreSQL-backed authorization
- secure export creation and download
- Redis/Celery queue handling
- MinIO object storage
- audit logging
- Prometheus, Loki, Grafana, and Uptime Kuma observability
- CI/CD workflow and automated tests
- incident runbooks and simulation documents

## Control Mapping

| Control area | Current implementation mapping | Evidence | Current state |
| --- | --- | --- | --- |
| Authentication | API validates issuer, audience, signature, expiration, and subject from Keycloak-issued tokens | `src/auth.py`, `keycloak/realm-export.json` | Implemented for local/demo scope |
| Authorization | Tenant roles come from PostgreSQL memberships and operations access comes from `users.internal_role` | `src/authz.py`, `src/db.py`, `tests/test_operations_summary.py` | Implemented |
| Tenant isolation | Job reads and downloads are tenant-scoped; worker reloads authoritative job context from PostgreSQL | `src/api.py`, `src/tasks.py`, `tests/test_exports.py` | Implemented |
| Queue trust boundary | Redis carries only `job_id`; worker does not trust queue-carried tenant context | `src/tasks.py`, `src/celery_app.py`, `tests/test_exports.py` | Implemented |
| Export delivery security | Completed exports are downloaded through the API after role and tenant checks | `src/api.py`, `src/storage.py`, `tests/test_exports.py` | Implemented |
| Audit logging | Security-relevant actions are written to `audit_events` | `src/db.py`, `src/api.py`, `src/tasks.py` | Implemented |
| Metrics and monitoring | API and worker emit Prometheus metrics; Grafana dashboards are provisioned | `src/metrics.py`, `observability/prometheus/`, `observability/grafana/` | Implemented |
| Log aggregation | Structured logs are shipped by Promtail to Loki | `src/logging_utils.py`, `observability/promtail/config.yml`, `observability/loki/local-config.yaml` | Implemented |
| Availability and dependency health | Uptime Kuma and bounded health checks in operations summary cover key dependencies | `docker-compose.yml`, `src/operations.py` | Partially implemented |
| CI/CD regression testing | GitHub Actions workflow runs Compose and API pytest in its current checked-in form | `.github/workflows/tests.yml` | Partially implemented |
| Incident response preparedness | Runbook and simulated incident documents exist for current risk scenarios | `docs/incident-runbook.md`, `docs/incident-simulation.md` | Implemented for coursework scope |

## Framework Notes

### SOC 2-style relevance

- Security:
  - authentication and authorization boundaries are central
  - secure export access and audit evidence are relevant
- Availability:
  - queue, worker, storage, and dependency visibility matter
  - incident response and recovery validation matter
- Confidentiality:
  - tenant isolation is the most important product concern

### CIS-style relevance

- account and access control management map to Keycloak plus PostgreSQL authorization
- audit log management maps to `audit_events`, Loki, and structured logging
- data recovery and availability expectations map only partially in the current repo because backup/restore automation is not demonstrated

### OWASP-style relevance

- Broken Access Control is directly relevant to tenant isolation and operations access
- Security Logging and Monitoring Failures is directly relevant to audit events, Loki, and Grafana
- ASVS is relevant for authn, authz, data protection, and logging expectations

## Current Limitations

- no formal certification evidence exists
- MFA enforcement is not demonstrated in the checked-in Keycloak realm
- backup and restore automation is not demonstrated
- the CI workflow still needs root-path and `.env` bootstrapping verification
- the local stack includes demo credentials and local admin surfaces unsuitable for production

## Current Submission Position

The repository demonstrates a meaningful compliance-oriented implementation and mapping exercise. It should be presented as:

- a mock SaaS platform
- a control-mapping and preparedness exercise
- not a certified or production-hardened compliant system
