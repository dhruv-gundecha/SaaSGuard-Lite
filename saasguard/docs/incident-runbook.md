# Incident Runbook

This runbook is aligned to the current SaaSGuard-Lite implementation. It covers the incident classes that the code, dashboards, and tests currently support most directly.

## Severity Levels

- `SEV-1`: cross-tenant exposure, broad authentication outage, or a failure that prevents most users from using the platform
- `SEV-2`: major export disruption, prolonged queue backlog, or dependency outage that blocks core workflows for many users
- `SEV-3`: localized failures, elevated denials, or degraded operations visibility without broad service loss

## Ownership

- Primary incident owner:
  - `ops_admin` for availability, queue, and dependency incidents
  - `soc_admin` for authn/authz anomalies, cross-tenant concerns, and suspicious denial spikes
- Supporting roles:
  - application engineer for API or worker regressions
  - platform/operator for Docker, Keycloak, MinIO, PostgreSQL, or Redis failures

## Escalation Guidance

- Escalate immediately to `SEV-1` if there is suspected cross-tenant disclosure.
- Escalate to the application owner if healthy dependencies plus degraded application behavior suggest a config or release regression.
- Treat system-wide auth failures separately from generic uptime failures because the Operations page itself may be unavailable during auth-wide incidents.

## Standard Response Structure

For every incident class:

1. Detect
2. Investigate
3. Respond
4. Recover
5. Verify

## Token Validation Failure Spike

### Severity

- default `SEV-2`
- escalate to `SEV-1` if most users cannot authenticate or if the source is suspicious token activity at scale

### Detect

- Grafana `Auth and Security / Token Validation Failures`
- Loki `event_name="auth.token_rejected"`
- user-visible `Invalid bearer token`, `Unknown user`, or missing tenant context
- Alert trigger: `SaaSGuard Authentication Failure Spike`

### Investigate

1. Check Uptime Kuma for API and Keycloak reachability.
2. Confirm the API is serving requests at all.
3. Query Loki for `auth.token_rejected`.
4. Review `error_type` in logs.
5. Compare `OIDC_ISSUER`, `OIDC_JWKS_URL`, and `OIDC_AUDIENCE` with the expected Keycloak realm/client settings.

### Respond

1. Correct the failing OIDC configuration or dependency state.
2. Restart or recreate the API if configuration changed.
3. Avoid changing authorization logic until token validation is confirmed healthy.
4. First response action: confirm whether the issue is token-validation drift or a broader Keycloak outage before restarting unrelated services.

### Recover

1. Restore correct API OIDC settings.
2. Confirm Keycloak JWKS reachability.
3. Re-test authenticated API requests.

### Verify

1. `/me` returns a valid user again.
2. tenant context resolves again.
3. `POST /exports` works for a valid user.
4. token validation failures stop rising.
5. no new matching Loki token-rejection events appear for the same failure mode.
6. Recovery validation: the alert returns to `Normal` after the incident window passes.

## OIDC Issuer Mismatch

### Severity

- default `SEV-2`
- can become `SEV-1` if it affects all logins and operators lose access to in-product investigation pages

### Detect

- Grafana token validation failures rise
- Loki shows `InvalidIssuerError`
- Uptime Kuma still shows API and Keycloak broadly reachable
- Alert trigger: `SaaSGuard Authentication Failure Spike`

### Investigate

1. Confirm the incident is not a generic Keycloak outage.
2. Compare the configured issuer against the real Keycloak realm issuer.
3. Verify the failure is in API validation, not browser login redirection.

### Respond

1. Restore the correct `OIDC_ISSUER`.
2. Recreate the API container.
3. First response action: compare the configured issuer against the real realm issuer before changing any other auth setting.

### Recover

1. Login through the frontend again.
2. Confirm `/me` resolves identity and memberships.

### Verify

1. valid bearer tokens are accepted again.
2. export creation works.
3. authorization and tenant context are restored.
4. Recovery validation: Grafana auth-failure rate returns to baseline and the alert clears.

## Authorization Denial Spike

### Severity

- default `SEV-3`
- escalate to `SEV-2` if it blocks legitimate workflows broadly
- escalate to `SEV-1` if it indicates or masks cross-tenant leakage

### Detect

- Grafana `Authorization Denials`
- audit-event denial spikes
- repeated `job.read_denied` or operations access denials
- Alert trigger: `SaaSGuard Authorization Denial Spike`

### Investigate

1. Determine whether the spike is expected policy enforcement or a regression.
2. Review denied action names and target types in audit events.
3. Check whether `X-Active-Tenant` usage is wrong or stale.
4. Determine whether the pattern is user error, client bug, or probing.

### Respond

1. Fix membership or tenant-selection regressions if legitimate users are blocked.
2. If suspicious probing exists, preserve logs and treat the behavior as a security review case.
3. First response action: determine whether the spike is expected enforcement, user error, or suspicious activity before changing access-control code.

### Recover

1. restore correct access path for legitimate users.
2. keep denied actions denied for unauthorized users.

### Verify

1. valid tenant workflows succeed.
2. denials return to expected levels.
3. no unintended operations access appears for tenant users.
4. Recovery validation: the authorization-denial alert clears after the spike ends.

## MinIO Outage

### Severity

- default `SEV-2`

### Detect

- rising `saasguard_worker_minio_upload_failures_total`
- failed jobs at upload stage
- download or completion failures
- MinIO unavailable in Uptime Kuma or direct checks
- Alert trigger: `SaaSGuard MinIO Upload Failure Spike`

### Investigate

1. Confirm whether the outage is isolated to MinIO.
2. Confirm the worker is still running.
3. Check MinIO credentials, bucket access, and console reachability.
4. Review worker logs for upload failures and retry behavior.

### Respond

1. restore MinIO service or configuration.
2. do not scale workers blindly until storage is healthy.
3. First response action: confirm whether the failure is a MinIO outage, bucket issue, or credential misconfiguration.

### Recover

1. confirm bucket reachability.
2. create a fresh export after recovery.

### Verify

1. a new export completes.
2. the CSV downloads successfully through the API.
3. MinIO upload failures stop increasing.
4. Recovery validation: the MinIO alert clears and no new upload-failure spikes are observed.

## Queue Backlog Growth

### Severity

- default `SEV-2`
- escalate to `SEV-1` if backlog is severe enough that users effectively cannot receive reports

### Detect

- Grafana `Global Queue Pressure`
- high `queued` and `retry_pending`
- high `oldest pending job age`
- Alert trigger: `SaaSGuard Queue Backlog Growth`

### Investigate

1. Check worker health first.
2. Check Redis, PostgreSQL, and MinIO health.
3. Compare export request rate against worker completion rate.
4. Review whether the backlog is demand-driven or failure-driven.

### Respond

1. fix the blocking dependency or worker failure mode.
2. apply temporary load controls if the queue is growing from request bursts.
3. First response action: verify whether the issue is worker-side, Redis-side, or downstream dependency-related before trying to scale anything.

### Recover

1. allow the worker to drain healthy backlog.
2. submit a fresh export to prove recovery.

### Verify

1. queue age starts falling.
2. completed exports increase again.
3. users can download fresh reports.
4. Recovery validation: the backlog alert clears after queue depth and oldest-age return below threshold.

## Worker Failure Spike

### Severity

- default `SEV-2`

### Detect

- rising worker failures and retries
- low completion rate
- export jobs stuck or failing
- Alert trigger: `SaaSGuard Export Failure Spike` and `SaaSGuard Worker Failure or Retry Spike`

### Investigate

1. Check `failure_stage` in metrics and job records.
2. Review worker logs for records-load, upload, or unexpected failure patterns.
3. Correlate failures with Redis, PostgreSQL, and MinIO health.

### Respond

1. address the failing stage rather than restarting everything blindly.
2. preserve evidence for repeated unexpected failures.
3. First response action: identify whether failures cluster in `records_load`, `upload`, or `unexpected` paths.

### Recover

1. restore the broken dependency or code path.
2. create a fresh export after mitigation.

### Verify

1. job completion resumes.
2. retries and failures return to normal.
3. download works for a newly completed export.
4. Recovery validation: worker failure and retry alerts return to `Normal`.

## Cross-Tenant Exposure or Suspected Exposure

### Severity

- always `SEV-1`

### Detect

- unexpected tenant data in job or export output
- authorization behavior inconsistent with membership rules
- audit or log evidence suggesting cross-tenant access was not denied

### Investigate

1. isolate the affected job IDs, tenant IDs, and users immediately.
2. preserve audit, log, and job-state evidence.
3. determine whether the failure is in read authorization, download authorization, or worker context handling.

### Respond

1. stop affected traffic or disable export/download functionality if scope is unknown.
2. do not treat this as a normal availability incident.

### Recover

1. fix the boundary failure.
2. re-run tenant-isolation tests before restoring normal operation.

### Verify

1. cross-tenant access is denied again.
2. authoritative worker-context behavior still holds.
3. secure download path still enforces tenant membership.
