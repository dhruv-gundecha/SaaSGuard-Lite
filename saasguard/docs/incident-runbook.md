# Incident Runbook

## Initial triage

Signals:

- Uptime Kuma shows one or more local stack monitors as `Down` or `Pending`
- Grafana service dashboards indicate a dependency outage or slow recovery

Actions:

1. Open `http://localhost:3002` and identify whether the first failure is at the edge (`frontend`, `Keycloak`) or in an internal dependency (`postgres`, `redis`, `minio`).
2. If only host-facing checks fail, compare them with the equivalent Docker-network checks to separate ingress problems from service failures.
3. Move to Grafana and Loki once Kuma identifies the failing service or dependency path.

## MinIO outage

Signals:

- `Service Health` dashboard shows rising `MinIO upload failures`
- worker logs show `worker.export.upload_failed`
- jobs accumulate in `retry_pending` or `failed`

Actions:

1. Check MinIO container health and console availability at `http://localhost:9001`.
2. Inspect Loki for `event_name="worker.export.upload_failed"`.
3. Verify bucket credentials in `.env`.
4. After restoring MinIO, create a fresh export to confirm completion.

## Token validation failure spike

Signals:

- `Auth and Security` dashboard shows rising `Token Validation Failures`
- API logs show `auth.token_rejected`

Actions:

1. Confirm Keycloak is reachable at `http://auth.saasguard.local:8081`.
2. Verify `OIDC_ISSUER`, `OIDC_JWKS_URL`, and `OIDC_AUDIENCE` in `.env`.
3. Confirm clients are using fresh tokens and not expired ones.
4. Query Loki for `event_name="auth.token_rejected"` and review `error_type`.

## Authorization denial spike

Signals:

- `Auth and Security` dashboard shows rising `Authorization Denials`
- audit events contain repeated denied actions

Actions:

1. Inspect recent audit records with a tenant admin token via `/audit-events`.
2. Query Loki for `event_name="auth.authorization_denied"` or `event_name="job.read_denied"`.
3. Verify membership and role seed data in PostgreSQL.
4. Check whether a multi-tenant user omitted `X-Active-Tenant`.

## Queue backlog growth

Signals:

- `Service Health` dashboard shows high `queued jobs` or increasing `oldest pending age`
- Prometheus shows low or zero worker completions

Actions:

1. Confirm the worker container is running.
2. Inspect worker metrics at `http://localhost:9101`.
3. Query Loki for `event_name="worker.job_failed"` or `event_name="worker.job_retried"`.
4. Check Redis and PostgreSQL reachability from the worker container.

## Worker failure spike

Signals:

- `Service Health` shows rising worker failures
- `Tenant Impact` shows failures concentrated in one tenant

Actions:

1. Use Loki to filter on `service="worker"` and the affected `tenant_id`.
2. Check `failure_stage` in `export_jobs`.
3. Confirm tenant-scoped data still exists in `tenant_records`.
4. Reproduce with a fresh export after fixing the dependency or data issue.
