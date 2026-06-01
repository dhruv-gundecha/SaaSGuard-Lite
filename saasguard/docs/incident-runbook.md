# Incident Runbook

This runbook is for SaaSGuard-Lite incident handling in the local exercise environment. It focuses on failures that affect Keycloak-backed authentication, tenant-scoped authorization, export processing, and export retrieval. It is an investigation aid, not proof that the system is production-ready.

# Initial Triage

Start from the first user-visible symptom and then separate availability failures from authentication and authorization failures.

Signals to collect at the start:

- user reports such as `Unknown user`, `No tenant scope`, `Invalid bearer token`, failed export creation, or failed export download
- Uptime Kuma status for `api`, `frontend`, `keycloak`, `postgres`, `redis`, `worker`, and other core services
- Grafana dashboard patterns, especially `Auth and Security` and service or worker health panels
- Loki event patterns for auth, authorization, and worker failures

Initial triage steps:

1. Reproduce the customer symptom in the UI or with the affected API path.
2. Check Uptime Kuma first to determine whether this is a simple service outage or a still-running system with failing requests.
3. If core services are up, move to Grafana to identify whether the pattern is primarily auth-related, authorization-related, or queue/worker-related.
4. Use Loki to confirm the event family and error types behind the metric spike.
5. Keep the investigation broad at first. Do not jump to a single root cause before validating what failed and what remained healthy.

Operational note:

- Operations Overview may not be accessible during a system-wide authentication incident because it depends on the same authentication path. During this type of incident, Grafana, Loki, and Uptime Kuma are the primary investigation tools.

# MinIO Outage

Signals:

- export creation may succeed but completion or download later fails
- worker failures or retries increase
- Loki shows storage-related worker errors such as upload failures
- Uptime Kuma or direct checks show MinIO unavailable

Investigation steps:

1. Check Uptime Kuma for MinIO reachability and whether the outage is isolated to MinIO or part of a wider stack problem.
2. Confirm the worker is still running so the symptom is not being caused by worker loss instead of storage loss.
3. Query Loki for worker storage failures and review whether failures are concentrated at upload or download stages.
4. Check MinIO container health, credentials, bucket configuration, and whether the MinIO console is reachable.
5. Review whether export jobs are building backlog in queued, retry-pending, or failed states while MinIO is down.

Recovery validation:

1. Confirm MinIO is reachable again.
2. Verify worker retries or new jobs can complete after restoration.
3. Create a fresh export after MinIO is restored.
4. Confirm the export reaches a successful state.
5. Download the newly created export and verify the artifact is retrievable end to end.

# Token Validation Failure Spike

This is the primary authentication incident pattern demonstrated in the recorded simulation.

Signals:

- `Auth and Security` dashboard shows `Token Validation Failures` increasing
- API logs show `auth.token_rejected`
- frontend shows `Unknown user`, `No tenant scope`, or `Invalid bearer token`

Investigation:

1. Confirm Keycloak is reachable.
2. Confirm API is reachable.
3. Check Uptime Kuma for service health.
4. Query Loki for `auth.token_rejected`.
5. Review `error_type` values.
6. Do not immediately assume configuration drift.
7. Consider malicious tokens, expired tokens, frontend token issues, and OIDC configuration drift.
8. Compare `OIDC_ISSUER`, `OIDC_JWKS_URL`, and `OIDC_AUDIENCE` against Keycloak configuration.
9. Restore correct configuration if mismatch is found.

Interpretation guidance:

- If Keycloak is down, the issue may be token acquisition or discovery related rather than issuer validation.
- If the API is down, fix availability first because auth symptoms may be secondary.
- If Uptime Kuma shows core services healthy but Grafana and Loki show rising token validation failures, treat this as an authentication-path regression until disproven.
- `InvalidIssuerError` strongly suggests issuer mismatch, but it still does not prove whether the cause is backend drift, malicious tokens from another issuer, or a frontend using the wrong identity provider. Check the actual configured issuer before concluding.

Recovery actions:

1. Restore the correct OIDC configuration values.
2. Recreate or restart the API container so the corrected values are loaded.
3. Re-test authenticated UI and API flows with a valid Keycloak-issued token.

Note:

- Operations Overview may not be accessible during a system-wide authentication incident because it depends on the same authentication path. During this type of incident, Grafana, Loki, and Uptime Kuma are the primary investigation tools.

# Authorization Denial Spike

Signals:

- rising authorization denials in Grafana
- repeated cross-tenant access attempts
- unauthorized Operations Overview access attempts
- suspicious or incorrect `X-Active-Tenant` usage

Investigation steps:

1. Determine whether denials are normal policy enforcement or an unexpected spike.
2. Review audit and Loki data for cross-tenant access attempts and repeated denied operations.
3. Check whether users are attempting unauthorized Operations Overview access with roles that should not have it.
4. Inspect requests for missing, stale, or incorrect `X-Active-Tenant` values.
5. Verify whether the denied principal should have access to the tenant or action they attempted.
6. Distinguish malicious probing from a frontend or membership regression before changing authorization logic.

Audit and log review focus:

- cross-tenant reads or writes that were correctly denied
- repeated denied admin or operations endpoints
- patterns showing one user or client repeatedly sending the wrong active tenant

# Queue Backlog Growth

Signals:

- queued jobs increasing
- oldest pending age increasing
- low worker completions

Investigation steps:

1. Confirm whether the worker container is running and stable.
2. Check Redis health because it is on the queue path.
3. Check PostgreSQL health because the worker depends on persisted job state and tenant data.
4. Review worker throughput versus backlog growth in Grafana.
5. Use Loki to see whether the worker is failing jobs, retrying them, or not receiving work at all.
6. Determine whether the backlog is caused by demand spike, worker failure, Redis issues, PostgreSQL issues, or a downstream dependency such as MinIO.

# Worker Failure Spike

Signals:

- worker failures increasing
- repeated failures at the same processing stage
- fresh exports not completing

Investigation steps:

1. Review worker failure metrics and confirm the spike is current rather than historical noise.
2. Check `failure_stage` values to identify whether jobs are failing on read, transform, persist, upload, or other stages.
3. Query Loki worker logs for matching failures and stack context.
4. Correlate worker failures with Redis, PostgreSQL, and MinIO health.
5. Apply the mitigation for the failing dependency or code path.
6. Validate with a fresh export after mitigation rather than assuming recovery from restored metrics alone.

# Recovery Validation

Recovery is not complete until both observability and user workflows return to expected behavior.

Validate the following:

1. user identity restored
2. tenant context restored
3. export creation works
4. export download works
5. auth failure metric stops increasing
6. no new `auth.token_rejected` events
7. dashboards return to normal

Additional guidance:

- Use a fresh login or valid token after auth recovery so stale client state does not confuse the result.
- Prefer a fresh export created after remediation when validating queue, worker, or storage recovery.
- Treat the absence of new errors over a short window as a positive signal, not proof that every edge case is resolved.
