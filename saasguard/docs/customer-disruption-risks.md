# Customer Disruption Risks

This document focuses on the highest operational risks that can interrupt customer use of SaaSGuard-Lite's export workflow:

`Keycloak login -> API authorization -> PostgreSQL job creation -> Redis queue carries only job_id -> worker reloads job context from PostgreSQL -> tenant-scoped CSV upload to MinIO -> download`

The emphasis here is customer disruption, not abstract infrastructure risk. A problem is high priority if it stops users from authenticating, creating exports, seeing job status, or downloading completed reports, or if it creates a severe trust incident such as cross-tenant exposure.

## 1. API or Frontend Container/Service Down

**Description**

If the FastAPI API or the React frontend is unavailable, the product becomes partially or fully unusable. The frontend is the main operator surface, and the API is the control plane behind login context, job creation, job listing, audit access, and download link generation.

**Customer impact**

- Users cannot log in through the frontend.
- Users cannot request exports with `POST /exports`.
- Users cannot view queued, processing, failed, or completed jobs.
- Users cannot retrieve fresh download links for completed exports.

**Likely causes**

- Container crash or restart loop in `api` or `frontend`
- Bad deployment image or broken startup command
- Environment/config drift such as bad OIDC, CORS, or backend URL settings
- Dependency outage that makes the API fail readiness even if the process is up

**Current controls**

- `/health` on the API for liveness checks
- Prometheus scrape of `api:8000/metrics`
- Uptime Kuma for edge availability checks
- Structured logs with request and correlation IDs
- Grafana `Service Health` dashboard for request rate, error rate, auth failures, and backlog signals

**Early alert metrics/signals**

- Uptime Kuma monitor failure for frontend or API
- `sum(rate(saasguard_api_requests_total{status_code=~"5.."}[5m]))`
- `histogram_quantile(0.95, sum by (le) (rate(saasguard_api_request_latency_seconds_bucket[5m])))`
- Request volume collapsing toward zero during expected business activity
- Logs containing repeated startup failures, dependency connection failures, or token validation errors immediately after deploy

**Mitigation/recovery actions**

1. Confirm whether only the frontend is down or whether the API is also failing.
2. Check Uptime Kuma first to see whether the failure is edge-only or service-wide.
3. Inspect `docker compose ps`, API logs, and frontend logs for crash loops or config errors.
4. If the API is up but degraded, inspect PostgreSQL, Keycloak, and MinIO before redeploying.
5. Roll back the last deployment or restore the previous image if the failure started immediately after a release.

## 2. DDoS or Malicious Export Request Burst

**Description**

SaaSGuard-Lite accepts export creation through a single API flow that persists a job and enqueues only `job_id`. If an attacker or buggy client repeatedly hits `POST /exports`, the API, PostgreSQL, Redis, and worker can all get saturated even without bypassing authorization.

**Customer impact**

- Legitimate users see slow responses or 5xx errors
- Export requests are accepted but sit in queue for too long
- Completed-job throughput drops while backlog grows
- Download availability looks healthy even though fresh exports are effectively unavailable

**Likely causes**

- Repeated `POST /exports` calls from one actor or a small set of actors
- Weak or missing request-rate controls at the API edge
- Expensive downstream processing causing queue growth after an intake spike
- Malicious automation targeting authenticated demo or low-friction accounts

**Current controls**

- Authorization checks before job creation
- PostgreSQL as source of truth for queued work
- Worker metrics for queue wait time and job throughput
- Tenant-scoped audit evidence for export requests

**Early alert metrics/signals**

- `sum(rate(saasguard_api_export_requests_created_total[5m]))`
- `sum(rate(saasguard_api_requests_total{path="/exports",method="POST"}[5m]))`
- `saasguard_queue_backlog_jobs`
- `saasguard_oldest_pending_job_age_seconds`
- Drop in worker completion rate compared with export creation rate

**Mitigation/recovery actions**

1. Confirm whether the spike is global or concentrated in one tenant or one role.
2. Compare export request rate with worker completion rate and queue age.
3. Apply temporary rate limiting or upstream traffic filtering.
4. Scale workers only after confirming the surge is legitimate enough to process.
5. Review audit events and logs to identify the caller pattern driving the burst.

## 3. Worker Backlog or Worker Failure

**Description**

The worker is the part of the system that turns a queued job into a downloadable CSV. If the Celery worker is down, unable to claim jobs, blocked on PostgreSQL, or failing uploads to MinIO, the API can still accept work while customers get stuck waiting.

**Customer impact**

- Export requests appear accepted but never finish
- Jobs remain `queued`, `retry_pending`, or `processing` for too long
- Customers may retry manually, making backlog worse
- Support sees "it says accepted but I never got my file"

**Likely causes**

- Worker container down or not connected to Redis
- Celery processing failure
- Redis transport issue delaying consumption
- PostgreSQL contention or query failures during job reload or tenant record fetch
- MinIO upload errors after CSV generation

**Current controls**

- Worker metrics endpoint on port `9101`
- Queue backlog and oldest pending age computed from PostgreSQL authoritative state
- Worker retry counters and failure-stage tracking
- Audit events for `export.completed` and `export.failed`
- Structured worker logs with `job_id`, `tenant_id`, and `correlation_id`

**Early alert metrics/signals**

- `sum(rate(saasguard_worker_jobs_started_total[5m]))`
- `sum(rate(saasguard_worker_jobs_completed_total[5m]))`
- `sum(rate(saasguard_worker_jobs_failed_total[5m]))`
- `sum(rate(saasguard_worker_job_retries_total[5m]))`
- `saasguard_queue_backlog_jobs`
- `saasguard_oldest_pending_job_age_seconds`
- `histogram_quantile(0.95, sum by (le) (rate(saasguard_worker_queue_wait_seconds_bucket[15m])))`
- No completed jobs in a recent window while new jobs continue to be created

**Mitigation/recovery actions**

1. Confirm the worker container is up and the metrics endpoint is reachable.
2. Check whether failures cluster at `records_load` or `upload`.
3. Inspect Redis reachability and PostgreSQL query health from the worker container.
4. If MinIO is failing, recover storage first instead of scaling workers.
5. After recovery, submit a fresh export and confirm queue age begins falling.

## 4. Cross-Tenant Data Exposure

**Description**

This is the highest trust-impacting product failure. SaaSGuard-Lite is multi-tenant, and the architecture is intentionally designed so the API authorizes memberships from the internal database and the worker reloads trusted tenant context from PostgreSQL instead of trusting queue payload fields. Any break in that model can expose one tenant's job or export to another tenant.

**Customer impact**

- Severe trust loss and likely incident response obligations
- One tenant may see another tenant's job metadata or exported CSV
- Customers can no longer trust the isolation model, even if the outage window is short

**Likely causes**

- Missing tenant filter in job reads or download lookup
- Broken membership check in the API
- Worker trusting `tenant_id` or `user_id` from Redis instead of reloading from PostgreSQL
- Object access pattern that makes export keys guessable or reusable without authorization

**Current controls**

- API resolves active tenant from internal memberships
- `get_job_for_tenant(job_id, tenant_id)` is used for scoped job reads
- Redis carries only `job_id`
- Worker reloads authoritative job state from PostgreSQL before export processing
- Audit events and denial metrics on cross-tenant access attempts
- Automated tests for queue payload safety and cross-tenant job denial

**Early alert metrics/signals**

- `sum(rate(saasguard_api_authorization_denials_total[5m]))`
- `sum(rate(saasguard_api_job_read_denials_total[5m]))`
- Audit events with `outcome="denied"` for `job.viewed`
- CI failures in trust-boundary tests around queue payload and tenant-scoped access
- Unusual repeated job-id probing in logs

**Mitigation/recovery actions**

1. Treat any suspected cross-tenant exposure as a security incident, not only an availability bug.
2. Confirm whether the issue is read-path authorization, worker context handling, or object download authorization.
3. Stop affected traffic or disable download issuance if scope is unclear.
4. Review audit events and logs by `job_id`, `tenant_id`, `user_id`, and `correlation_id`.
5. Re-run tenant-isolation tests before restoring normal operation.

## 5. Authentication or Keycloak Misconfiguration

**Description**

Keycloak is responsible for authentication, but the API validates issuer, JWKS, and audience configuration before mapping the subject to an internal user. A drift in issuer URL, JWKS URL, audience, or Keycloak availability can make valid users look unauthenticated or unprovisioned.

**Customer impact**

- Users cannot log in successfully through the frontend
- The API rejects valid bearer tokens
- Existing sessions may fail when tokens refresh
- Operators may misdiagnose the issue as an app outage when it is actually auth configuration drift

**Likely causes**

- `OIDC_ISSUER` mismatch
- `OIDC_JWKS_URL` mismatch or Keycloak cert endpoint unavailable
- `OIDC_AUDIENCE` mismatch
- Keycloak container down or unhealthy
- Realm import drift after local configuration changes

**Current controls**

- Explicit issuer/audience validation in the API
- `saasguard_api_auth_failures_total`
- Structured auth logs such as `auth.token_rejected`
- Uptime and health checks for the auth dependency path

**Early alert metrics/signals**

- `sum(rate(saasguard_api_auth_failures_total[5m]))`
- Uptime Kuma Keycloak monitor failure
- Logs with `event_name="auth.token_rejected"`
- Sudden increase in 401 responses while non-auth endpoints remain healthy

**Mitigation/recovery actions**

1. Verify Keycloak container health and external reachability first.
2. Compare configured issuer, JWKS URL, and audience against the actual realm/client settings.
3. Check whether the failure started after a realm import or environment change.
4. Test with a freshly minted token after correcting configuration.
5. If only one deployment is bad, roll back the auth-related config change instead of rotating unrelated services.

## 6. PostgreSQL or MinIO Disruption

**Description**

PostgreSQL is the authoritative source for users, memberships, jobs, and audit events. MinIO stores the finished export objects. If PostgreSQL is down, the product loses truth for authorization and job state. If MinIO is down, completed exports cannot be uploaded or downloaded even if job execution otherwise works.

**Customer impact**

- Jobs cannot be created or status cannot be read if PostgreSQL is unavailable
- Authorization and audit functionality degrade with PostgreSQL disruption
- Exports cannot complete or be downloaded if MinIO is unavailable or misconfigured
- The system may accept some work but fail later in the pipeline

**Likely causes**

- PostgreSQL unavailable or startup/migration failure
- Broken credentials or connection string
- MinIO unavailable, bucket missing, or bad access keys
- Transient storage/network errors during upload

**Current controls**

- Worker DB query failure metric with bounded `operation` label
- MinIO upload failure metric
- Job failure stage persisted in PostgreSQL
- Grafana `Service Health` dependency failure panel
- Incident runbook entries for MinIO and backlog recovery

**Early alert metrics/signals**

- `sum(rate(saasguard_worker_db_query_failures_total[5m]))`
- `sum(rate(saasguard_worker_minio_upload_failures_total[5m]))`
- `sum(rate(saasguard_api_requests_total{status_code=~"5.."}[5m]))`
- Rising failed jobs with `failure_stage="upload"`
- Queue backlog rising because jobs cannot complete

**Mitigation/recovery actions**

1. Separate database issues from storage issues before restarting everything.
2. If PostgreSQL is down, restore the source of truth before accepting more traffic.
3. If MinIO is down, expect retries and eventual failed jobs; fix storage before replaying work.
4. Validate bucket existence and credentials after MinIO recovery.
5. Submit a fresh export and confirm end-to-end completion, not just service health.
