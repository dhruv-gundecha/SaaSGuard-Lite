# Introduction

Compliance matters for a multi-tenant SaaS product because the platform is simultaneously handling identity, authorization, shared infrastructure, customer data, asynchronous processing, and operational visibility. In SaaSGuard-Lite, a single mistake in authorization, export handling, or observability can become a cross-tenant confidentiality incident rather than a single-user bug.

For this product, the most relevant baseline is the AICPA SOC 2 Trust Services Criteria for Security, Availability, and Confidentiality. The criteria are broad control objectives rather than implementation checklists, so this document maps them to the system’s architecture and supplements them with CIS Controls v8 and OWASP guidance.

# Authentication and Access Control

The strongest compliance expectation for a multi-tenant SaaS platform is that identity and authorization are separate, centrally enforced, and resistant to client-side bypass.

Relevant expectations:

- Identity management should rely on a managed identity provider or equivalent controls for user lifecycle, account status, and credential assurance.
- MFA should be available for privileged access and, for production-grade deployments, generally required for administrators and other sensitive roles.
- Least privilege should be enforced so users receive only the minimum tenant and platform access needed.
- Role-based access control should be enforced server-side, not only in the UI.
- Separation of duties should distinguish tenant administration from platform-wide operational or security administration.
- Session management should use short-lived tokens, server-side validation, secure logout behavior, and clear session boundaries.

Product mapping:

- Keycloak provides OIDC identity, while the FastAPI API validates issuer, audience, signature, and expiration before mapping `sub` to an internal user record.
- FastAPI authorization decisions are made server-side after identity is established.
- PostgreSQL `memberships` records resolve tenant roles (`viewer`, `analyst`, `tenant_admin`) instead of trusting browser state or token role claims.
- Platform-wide operations access is separately controlled through `users.internal_role` (`soc_admin`, `ops_admin`).
- Authorization enforcement happens in backend code paths such as `require_role()` and `require_operations_role()`.
- Multi-tenant users must explicitly choose an active tenant when more than one membership exists.

Why this matters to SOC 2:

- Security criteria expect logical access controls that restrict system access to authorized users and roles.
- Confidentiality depends on strong authorization boundaries, especially where the same platform processes multiple customers’ data.

Secondary references:

- CIS Control 5 emphasizes account management for user, administrator, and service accounts.
- CIS Control 6 emphasizes creating, assigning, managing, and revoking privileges.
- OWASP ASVS is a testing-oriented baseline for authentication, session management, and access control.
- OWASP Top 10 Broken Access Control warns that access control must be enforced in trusted server-side code, deny by default, and log access control failures.

# Tenant Data Isolation

For a multi-tenant SaaS platform, tenant isolation is one of the most important confidentiality requirements.

Relevant expectations:

- Tenant data must be logically separated throughout API reads, writes, exports, and background processing.
- Object access must enforce tenant ownership before a file is returned.
- The system should prevent cross-tenant disclosure even if a user guesses object identifiers or job identifiers.
- Asynchronous workers should reload trusted authorization context from a durable system of record instead of trusting queue payload fields supplied earlier in the flow.

Product mapping:

- Tenant-scoped authorization is tied to `tenant_id` membership checks.
- Job reads use tenant-aware lookups rather than unrestricted reads when the endpoint is tenant-scoped.
- Redis carries only `job_id` as queue payload.
- The Celery worker reloads authoritative tenant context from PostgreSQL before exporting data.
- Completed export downloads still flow through the API so tenant authorization is re-checked before the CSV is streamed.

Why this matters to SOC 2:

- Security and Confidentiality both require prevention of unauthorized disclosure.
- In a SaaS context, cross-tenant disclosure is usually a higher-severity failure than a normal application bug because the platform boundary between customers has failed.

Secondary references:

- OWASP Top 10 Broken Access Control calls out record ownership enforcement and protection against insecure direct object references.
- OWASP ASVS access control requirements are directly relevant to tenant-scoped object and record authorization.

# Audit Logging and Monitoring

A compliant SaaS environment needs more than application logs. It needs durable audit evidence, operational telemetry, and usable security signals.

Relevant expectations:

- Security-relevant events should be recorded in an audit trail.
- Logs and audit records should support investigation, incident reconstruction, and detection of repeated abuse.
- Monitoring should cover authentication failures, authorization denials, export failures, dependency health, and platform degradation.
- Log retention should be defined and implemented.
- Correlation identifiers and consistent timestamps should support cross-system investigation.

Product mapping:

- PostgreSQL `audit_events` provide durable application audit evidence.
- Structured JSON logs include `correlation_id`, `request_id`, `tenant_id`, `user_id`, `job_id`, and event outcome fields.
- Loki aggregates logs shipped by Promtail.
- Prometheus collects API and worker metrics.
- Grafana provides operational dashboards for service health, tenant impact, and auth/security signals.
- Authorization denials and export activity are surfaced through both logs and metrics.
- Incident detection for this product depends on correlating `audit_events`, Loki logs, Prometheus counters, and Grafana dashboards rather than relying on one signal source.

Why this matters to SOC 2:

- Security criteria expect monitoring and incident-detection capability.
- Availability criteria rely on telemetry to detect degradation before it becomes a prolonged outage.
- Confidentiality incidents are difficult to investigate without durable and attributable evidence.

Secondary references:

- CIS Control 8 requires organizations to define logging requirements, collect audit logs, centralize them where possible, retain them, and review them for anomalies.
- OWASP Top 10 Security Logging and Monitoring Failures warns that missing logs for logins, failed logins, and high-value transactions can prevent breach detection and response.

# Availability and Operational Resilience

SOC 2 Availability is less about “five nines” marketing and more about whether the service can detect failure, understand dependencies, recover in a controlled way, and meet stated commitments.

Relevant expectations:

- The service should monitor critical paths and dependencies.
- Operators should have health and backlog visibility for API, database, queue, worker, storage, and identity provider components.
- Alerting should exist for outages, degradation, failed jobs, and dependency failures.
- Backup and recovery procedures should be documented, protected, and tested.
- Recovery expectations should be tied to business impact, not only component uptime.

Product mapping:

- Uptime Kuma provides edge and dependency availability checks.
- Prometheus and Grafana provide metrics and dashboards for API health, export backlog, worker failures, dependency health, and auth/security signals.
- The Operations Overview frontend page summarizes global operational state for internal roles.
- PostgreSQL, Redis, MinIO, and Keycloak health are explicitly part of the operational model.
- Administrative access control matters here because Grafana, Loki, Prometheus, MinIO, and the Operations Overview can expose cross-tenant operational context if platform roles are not separated from tenant roles.

Why this matters to SOC 2:

- Availability criteria focus on whether the system is available for operation and use as committed or agreed.
- A SaaS platform with asynchronous exports must monitor not only request uptime but also whether jobs are actually completing and downloadable.

Secondary references:

- CIS Control 11 requires a data recovery process, automated backups, protection of recovery data, and separation or isolation of recovery data.

# Data Protection

Data protection requirements apply both to stored tenant data and to generated export artifacts.

Relevant expectations:

- Sensitive or tenant-confidential data should be stored only where necessary and protected in transit and at rest.
- Export files should not be exposed through direct unauthenticated object-storage access.
- Download endpoints should verify authenticated user identity, tenant ownership, and correct export state before returning data.
- Logs should avoid secrets, raw bearer tokens, and unnecessary sensitive payloads.
- Storage used for recovery should receive controls comparable to production data.

Product mapping:

- MinIO stores generated export objects.
- Browser downloads are served through the API rather than direct MinIO access, preserving authorization checks.
- The download endpoint checks for an authenticated user, matching tenant membership, authorized role, completed job status, and object availability.
- Application logs avoid raw JWTs, passwords, and CSV contents.

Why this matters to SOC 2:

- Confidentiality criteria require protection of information designated as confidential.
- Security criteria require that interfaces and storage paths not become unauthorized disclosure paths.

Secondary references:

- OWASP ASVS includes dedicated sections for data protection and secure session handling.
- OWASP Top 10 Broken Access Control and Logging/Monitoring guidance are especially relevant to secure export delivery and denial visibility.

# Sources

Primary and secondary sources used for this requirement mapping:

1. AICPA, *2017 Trust Services Criteria (With Revised Points of Focus – 2022)*  
   https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022?Jid=CppDev20110217

2. AICPA, *SOC 2 Reporting on an Examination of Controls at a Service Organization Relevant to Security, Availability, Processing Integrity, Confidentiality, or Privacy*  
   https://www.aicpa-cima.com/cpe-learning/publication/soc-2-reporting-on-an-examination-of-controls-at-a-service-organization-relevant-to-security-availability-processing-integrity-confidentiality-or-privacy

3. CIS, *CIS Critical Security Control 5: Account Management*  
   https://www.cisecurity.org/controls/account-management

4. CIS, *CIS Critical Security Control 6: Access Control Management*  
   https://www.cisecurity.org/controls/access-control-management

5. CIS, *CIS Critical Security Control 8: Audit Log Management*  
   https://www.cisecurity.org/controls/audit-log-management

6. CIS, *CIS Critical Security Control 11: Data Recovery*  
   https://www.cisecurity.org/controls/data-recovery

7. CIS Controls Navigator v8, safeguards 8.1, 8.2, 8.5, 8.9, 8.10, 8.11, 11.1, 11.2, and 11.3  
   https://www.cisecurity.org/controls/cis-controls-navigator/v8

8. OWASP, *Application Security Verification Standard (ASVS)*  
   https://owasp.org/www-project-application-security-verification-standard/

9. OWASP Developer Guide, *ASVS*  
   https://devguide.owasp.org/en/06-verification/01-guides/03-asvs/

10. OWASP Top 10:2025, *A01 Broken Access Control*  
    https://owasp.org/Top10/2025/A01_2025-Broken_Access_Control/

11. OWASP Top 10:2021, *A09 Security Logging and Monitoring Failures*  
    https://owasp.org/Top10/2021/A09_2021-Security_Logging_and_Monitoring_Failures/
