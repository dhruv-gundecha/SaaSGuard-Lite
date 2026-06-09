# Customer Disruption Risks

This document focuses on the highest customer-impacting risks in the current SaaSGuard-Lite implementation. It is based on the running architecture, current metrics, and current test coverage.

## Critical Path

```text
Keycloak login
  -> API token validation
  -> tenant authorization
  -> PostgreSQL job creation
  -> Redis queue transport (job_id only)
  -> worker reloads authoritative context from PostgreSQL
  -> MinIO object upload
  -> API-mediated export download
```

The largest disruptions are the ones that break one or more steps in this path or create a cross-tenant trust failure.

## 1. Authentication-path failure

### Description

The UI may still load while authenticated API behavior fails because Keycloak, issuer configuration, audience configuration, or JWKS validation is wrong.

### Customer impact

- users cannot establish a valid application session
- exports cannot be requested
- tenant context cannot be resolved
- internal operators may also lose access to the Operations page

### Current signals

- `saasguard_api_auth_failures_total`
- Grafana `Auth and Security / Token Validation Failures`
- Loki `event_name="auth.token_rejected"`
- Uptime Kuma and Keycloak reachability checks

### Current mitigation posture

- strict OIDC validation in `src/auth.py`
- runbook guidance for auth failure spikes and issuer mismatch
- documented incident simulation for the OIDC issuer mismatch scenario

## 2. Cross-tenant access failure

### Description

A failure in job lookup, download authorization, tenant resolution, or worker context handling could expose one tenant’s data to another.

### Customer impact

- highest-severity confidentiality event
- loss of trust in the platform’s tenant boundary
- likely incident-response and reporting obligations in a real environment

### Current signals

- `saasguard_api_job_read_denials_total`
- `saasguard_api_authorization_denials_total`
- audit events with `authorization.denied`
- Loki `job.read_denied`

### Current mitigation posture

- tenant-scoped lookups for job reads
- secure API download path
- queue payload limited to `job_id`
- worker reloads authoritative context from PostgreSQL
- automated backend tests for cross-tenant denial and worker trust boundary

## 3. Export pipeline disruption

### Description

The API may accept work while the worker, Redis, PostgreSQL, or MinIO path fails to complete exports.

### Customer impact

- queued jobs grow
- expected report delivery time degrades
- users may retry exports and make backlog worse

### Current signals

- `saasguard_queue_backlog_jobs`
- `saasguard_oldest_pending_job_age_seconds`
- worker started/completed/failed metrics
- worker retry and MinIO failure metrics
- Grafana `Tenant Impact / Global Queue Pressure`

### Current mitigation posture

- retry tracking in `export_jobs`
- worker failure metrics
- MinIO upload failure instrumentation
- queue and dependency runbook coverage

## 4. MinIO outage or object-storage misconfiguration

### Description

Exports may finish generating rows but still fail to upload or download if object storage is unavailable or misconfigured.

### Customer impact

- exports remain unavailable even if the API and worker are up
- completed downloads fail
- users perceive the platform as unreliable

### Current signals

- `saasguard_worker_minio_upload_failures_total`
- failed jobs with `failure_stage="upload"`
- Loki worker upload failure logs
- Uptime Kuma and MinIO console checks

### Current mitigation posture

- worker upload failure metrics and retries
- runbook coverage for MinIO outage
- manual verification guidance for induced MinIO failure

## 5. Authorization denial spike

### Description

A surge in denials can reflect user confusion, client bugs, tenant-selection problems, or active probing of protected resources.

### Customer impact

- broken workflows for legitimate users
- increased support burden
- possible early signal of a security issue

### Current signals

- `saasguard_api_authorization_denials_total`
- audit-event denials
- Grafana `Auth and Security / Authorization Denials`
- operations-summary security panel

### Current mitigation posture

- backend role checks for tenant and internal-role paths
- audit evidence for denied actions
- runbook coverage for denial spikes

## 6. Dashboard or observability access misuse

### Description

Operations tooling can expose global platform state, dependency health, and logs that are broader than tenant-scoped product data.

### Customer impact

- possible operational data leakage
- overbroad operator access
- weaker isolation between tenant-facing and platform-facing views

### Current signals

- access-control tests for `/operations/summary`
- frontend operations-nav visibility tests
- internal-role logic in `/me`

### Current mitigation posture

- backend restriction to `soc_admin` and `ops_admin`
- frontend hides Operations navigation unless the API session allows it
- documentation treats observability as a controlled surface, not a general tenant feature

## Prioritized Risk Summary

High priority:

1. Cross-tenant access failure
2. Authentication-path failure
3. Export pipeline disruption
4. MinIO outage

Medium priority:

1. Authorization denial spike
2. Dashboard and observability access misuse

## Current Best Next Steps

1. Keep CI and security tests aligned with OIDC contract failures.
2. Add stronger workflow validation for `.env` bootstrapping and frontend build.
3. Preserve the queue trust boundary and secure download model as core design constraints.
