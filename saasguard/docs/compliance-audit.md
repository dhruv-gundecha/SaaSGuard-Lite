# Scope

SaaSGuard-Lite is a mock multi-tenant SaaS platform with:

- FastAPI API
- PostgreSQL as the authoritative system of record
- Redis as the transport-only queue
- Celery worker for export generation
- Keycloak OIDC authentication
- MinIO object storage
- Grafana, Prometheus, Loki, and Promtail for observability
- Uptime Kuma for availability checks
- Tenant-scoped authorization and audit logging
- Operational dashboards, including an internal Operations Overview

This audit is intentionally conservative. It evaluates what the repository and tests currently demonstrate. It does not claim formal SOC 2 compliance.

# Compliance Control Review

## Authentication

- Requirement: Authenticate users through a trusted identity system and validate tokens server-side before granting application access.
- Current Implementation: Keycloak provides OIDC identity. The API validates bearer tokens for issuer, audience, signature, expiration, and `sub`, then maps the identity to an internal user record.
- Status: Implemented
- Evidence: `src/auth.py`, `src/api.py`, `frontend/src/auth/AuthProvider.tsx`, `frontend/src/lib/keycloak.ts`, `docs/architecture.md`
- Gap: The implementation proves token validation, but this audit does not verify production hardening of Keycloak itself.
- Recommendation: Keep identity externalized and document production IdP hardening assumptions separately.

## Authorization

- Requirement: Enforce role-based access control on the server for tenant and platform actions.
- Current Implementation: Tenant roles are enforced through `require_role()`. Platform-wide operations access is enforced through `require_operations_role()`. The frontend hides operations navigation, but the backend remains the source of truth.
- Status: Implemented
- Evidence: `src/authz.py`, `src/api.py`, `frontend/src/lib/authorization.ts`, `frontend/src/components/AppShell.tsx`, `tests/test_operations_summary.py`
- Gap: No documented periodic review of role assignments.
- Recommendation: Add an access review process and document privileged-role approval criteria.

## Tenant Isolation

- Requirement: Prevent cross-tenant reads, downloads, and background-processing mix-ups.
- Current Implementation: Tenant membership is required for tenant-scoped operations. Job reads use tenant-aware lookups. The worker reloads authoritative job context from PostgreSQL instead of trusting Redis payload fields.
- Status: Implemented
- Evidence: `src/api.py`, `src/db.py`, `src/tasks.py`, `tests/test_exports.py`, `docs/architecture.md`
- Gap: Isolation is application-enforced; there is no evidence of database row-level security or equivalent datastore-native controls.
- Recommendation: Consider stronger database-side isolation if the product moves beyond mock/demo scope.

## Audit Logging

- Requirement: Record security-relevant events in a durable, reviewable audit trail.
- Current Implementation: PostgreSQL `audit_events` stores export requests, job views, denials, export completions, export failures, and export downloads. The download path now records denied cross-tenant download attempts as durable audit events.
- Status: Partially Implemented
- Evidence: `src/db.py`, `sql/migrations/002_export_jobs_and_audit.sql`, `src/api.py`, `src/tasks.py`, `tests/test_exports.py`
- Gap: Audit scope is meaningful but still narrow. There is no documented retention or formal review workflow tied to these records.
- Recommendation: Define required audited event classes, retention, review ownership, and escalation criteria.

## Monitoring

- Requirement: Monitor service health, failures, and security signals across core components.
- Current Implementation: Prometheus metrics, structured logs, Loki ingestion, and Grafana dashboards exist for API, worker, export, and security signals.
- Status: Partially Implemented
- Evidence: `src/metrics.py`, `src/logging_utils.py`, `src/operations.py`, `observability/`, `docs/architecture.md`
- Gap: The repository shows dashboards and metrics, but not a complete alerting policy or verified on-call detection workflow.
- Recommendation: Define alert thresholds, owners, and response expectations for critical conditions.

## Observability

- Requirement: Provide enough correlated telemetry across logs, metrics, and health surfaces to investigate tenant-impacting and security-impacting events.
- Current Implementation: The stack includes Prometheus, Grafana, Loki, Promtail, Uptime Kuma, and an internal Operations Overview that summarizes API health, worker state, security signals, and dependency status.
- Status: Partially Implemented
- Evidence: `observability/`, `src/operations.py`, `frontend/src/pages/OperationsPage.tsx`, `README.md`
- Gap: Correlated telemetry exists, but the product does not yet demonstrate complete alert wiring, historical investigation policy, or access hardening for every external observability tool.
- Recommendation: Treat observability as a controlled security surface, not just an operator convenience, and document ownership for dashboards, alerts, and retained evidence.

## Operational Visibility

- Requirement: Give operators enough global visibility to detect customer-impacting failures without exposing cross-tenant data to normal tenant users.
- Current Implementation: An Operations Overview page summarizes global health and links to Grafana, Loki, Prometheus, Uptime Kuma, and MinIO. Tenant users do not receive this view.
- Status: Implemented
- Evidence: `src/api.py`, `src/authz.py`, `frontend/src/pages/OperationsPage.tsx`, `frontend/src/components/AppShell.tsx`, `tests/test_operations_summary.py`
- Gap: The page exists, but separate observability systems still need their own access control outside the application.
- Recommendation: Ensure external observability tools are also protected with role-appropriate access controls.

## Export Security

- Requirement: Allow downloads only for authenticated, authorized users and only for completed tenant-owned exports.
- Current Implementation: The download endpoint requires an authenticated user, verifies tenant membership, checks viewer-or-higher role, requires `completed` status, requires an `object_key`, and then streams the object through the API.
- Status: Implemented
- Evidence: `src/api.py`, `src/storage.py`, `tests/test_exports.py`, `README.md`
- Gap: No signed-download expiration model or separate anti-abuse/rate-limiting layer is shown for download requests.
- Recommendation: Add rate-limiting and consider short-lived download issuance if the product expands.

## MinIO Access Model

- Requirement: Object storage should remain an internal storage layer, not a public authorization bypass around application controls.
- Current Implementation: Export objects are stored in MinIO, but browser downloads still route through the FastAPI API. The code fetches objects with server-side credentials and returns CSV content only after application authorization passes.
- Status: Implemented
- Evidence: `src/storage.py`, `src/api.py`, `README.md`, `docs/architecture.md`
- Gap: The local stack still exposes a MinIO console for development, so the broader administrative-access posture around storage is not compliance-grade by default.
- Recommendation: Keep object delivery behind the application in higher environments and separately harden MinIO administrative access.

## Secrets Handling

- Requirement: Store and manage secrets securely, with least exposure and no hard-coded production credentials.
- Current Implementation: Local development secrets and passwords are embedded in repo-managed config and demo realm data.
- Status: Not Implemented
- Evidence: `keycloak/realm-export.json`, `src/config.py`, `README.md`
- Gap: Demo credentials, client secrets, and default passwords are present in the repository, which is incompatible with a real compliance posture.
- Recommendation: Move secrets to environment- or secret-manager-backed delivery and remove repo-stored shared credentials from any non-demo deployment path.

## Incident Detection

- Requirement: Detect suspicious activity and operational failures early enough to investigate and respond.
- Current Implementation: The system emits auth-failure metrics, authorization-denial metrics, structured logs, and audit events. Runbooks and operational-risk documents exist.
- Status: Partially Implemented
- Evidence: `src/api.py`, `src/metrics.py`, `docs/incident-runbook.md`, `docs/customer-disruption-risks.md`, `docs/manual-tests-and-missing-alerts.md`
- Gap: There is no evidence of automated alert delivery, ticketing integration, or a formal incident-severity process.
- Recommendation: Add alert routing and a lightweight incident-response policy.

## Availability Monitoring

- Requirement: Monitor uptime and critical dependency health.
- Current Implementation: Uptime Kuma is part of the stack, and the operations logic actively checks PostgreSQL, Redis, MinIO, and Keycloak health.
- Status: Partially Implemented
- Evidence: `src/operations.py`, `docker-compose.yml`, `frontend/src/pages/OperationsPage.tsx`
- Gap: The repo does not show agreed service objectives, paging thresholds, or evidence that monitors are continuously validated.
- Recommendation: Define SLO/SLA targets and test monitoring coverage against those targets.

## Backup/Recovery

- Requirement: Maintain protected backups and a tested recovery process.
- Current Implementation: The repository contains discussion of recovery expectations and manual tests, but no demonstrated automated backups or verified restoration tests.
- Status: Not Implemented
- Evidence: `docs/manual-tests-and-missing-alerts.md`, `docs/incident-runbook.md`
- Gap: No backup schedule, no recovery-data protection evidence, and no restore verification evidence are present.
- Recommendation: Implement documented backups, protect recovery data, and run restoration drills.

## Administrative Access Controls

- Requirement: Limit platform-wide administrative and observability access to approved internal roles.
- Current Implementation: The application restricts `/operations/summary` and the Operations page to `soc_admin` and `ops_admin`.
- Status: Partially Implemented
- Evidence: `src/authz.py`, `src/api.py`, `frontend/src/pages/OperationsPage.tsx`, `tests/test_operations_summary.py`
- Gap: The repo also documents default Grafana credentials and local administrative surfaces, so the broader admin-access story is not yet compliance-grade.
- Recommendation: Harden administrative credentials and centralize privileged-access policy for observability tooling and storage consoles.

## Log Retention

- Requirement: Define and enforce retention for operational logs and audit evidence.
- Current Implementation: Audit events are stored durably in PostgreSQL and logs are centralized into Loki, but no retention policy is documented in the repository.
- Status: Not Implemented
- Evidence: `src/db.py`, `observability/loki/local-config.yaml`, `docs/architecture.md`
- Gap: There is no documented retention period, review schedule, or evidence that retention aligns with investigative needs.
- Recommendation: Document retention targets for audit logs, app logs, metrics, and exported evidence, then configure systems to match.

## MFA Enforcement

- Requirement: Require MFA for privileged access and, depending on customer commitments, broader user populations.
- Current Implementation: Keycloak is the identity provider, but the checked-in realm export shows password-based local users and no evidence of required MFA flows or policies.
- Status: Not Implemented
- Evidence: `keycloak/realm-export.json`
- Gap: MFA capability may exist in Keycloak as a product, but this repository does not demonstrate MFA enforcement for any role.
- Recommendation: Define MFA policy and verify it in the deployed realm, starting with `soc_admin`, `ops_admin`, and tenant administrators.

## Least Privilege

- Requirement: Grant users and services only the access they need, and review that access periodically.
- Current Implementation: Tenant roles and separate internal operations roles are implemented. Export downloads and audit access are role-gated.
- Status: Partially Implemented
- Evidence: `src/authz.py`, `src/api.py`, `sql/migrations/001_core_schema.sql`, `README.md`
- Gap: Least privilege is present in application roles, but there is no periodic access review, no documented service-account minimization, and no hardened secret-management layer.
- Recommendation: Add scheduled access reviews and explicitly document privileged account inventory and ownership.

## Least Privilege Database Access

- Requirement: Database access should be scoped so applications and operators do not receive broader privileges than necessary.
- Current Implementation: PostgreSQL is the source of truth for users, memberships, jobs, and audit events, but this repository does not show separate restricted database roles for API, worker, migrations, and administrative access.
- Status: Not Implemented
- Evidence: `src/config.py`, `src/db.py`, `sql/migrations/`, `docker-compose.yml`
- Gap: The code demonstrates tenant-aware queries, but not database-role separation or least-privilege credentials at the datastore layer.
- Recommendation: Introduce separate database roles for application runtime, migrations, and administration, then document which paths require elevated privileges.

## CI/CD Testing

- Requirement: Compliance-relevant controls should be regression-tested in CI so security behavior does not silently drift.
- Current Implementation: GitHub Actions runs the existing `pytest` suite on push and pull request activity. Tests cover export creation, tenant isolation, worker trust boundaries, operations-summary access control, and download authorization behavior.
- Status: Partially Implemented
- Evidence: `README.md`, `docs/full-ci-cd-gaps.md`, `tests/`
- Gap: The repository does not show frontend security tests in CI, secret scanning beyond defaults, dependency scanning, image scanning, or broader authorization regression coverage.
- Recommendation: Expand CI to cover frontend build validation, additional authz scenarios, dependency and container scanning, and checks for dev-only configuration drift.

# Compliance Improvement Plan

Priority actions for the next iteration:

1. Restrict Operations Overview to SOC/Admin roles  
   Current state: implemented in the backend and frontend.  
   Next step: extend the same access-control standard to Grafana, Loki, MinIO, and other external operator tools.

2. Harden privileged access controls  
   Remove default/shared admin credentials from non-demo paths, inventory privileged accounts, and document approval and revocation processes.

3. Verify MFA requirements  
   Configure and test required MFA for privileged roles in Keycloak, then document the policy.

4. Improve backup/recovery procedures  
   Add protected backups, documented restore steps, and restoration drills with evidence.

5. Document log retention policy  
   Define retention periods for audit records, application logs, metrics, and related evidence stores.

6. Add periodic access review process  
   Review internal roles, tenant-admin assignments, and service accounts on a scheduled basis.

# Practical Product Updates Completed During This Audit

- Operations Overview access was verified as restricted to `soc_admin` and `ops_admin` users at both backend and frontend layers.
- Export download success events already existed and denied cross-tenant download attempts were added to the durable audit trail.
- Authorization-denial metrics and logs were verified to exist for request-level 403s and key authorization paths.
- The secure export download path was verified to require authentication, tenant ownership, authorized role, completed status, and object availability.

# References

1. AICPA Trust Services Criteria (SOC 2)
2. CIS Controls v8.1
3. OWASP ASVS 4.0.3
4. OWASP Top 10 2021
5. NIST SP 800-61 Incident Handling Guide
6. NIST SP 800-53 Access Control Family
