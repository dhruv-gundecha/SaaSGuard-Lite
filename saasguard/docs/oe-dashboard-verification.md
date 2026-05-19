# OE Dashboard Verification

This document records how the provisioned Grafana dashboards were verified against live SaaSGuard-Lite behavior and which metrics power the key operational panels.

## Verified Dashboards

- `Service Health`
- `Tenant Impact`
- `Auth and Security`

## Validation Snapshot

Validation run date: `2026-05-18` in the local Docker Compose stack.

- `./scripts/verify_oe_metrics.sh` passed after confirming the API metrics from the `api` container and worker metrics from the `worker` container independently.
- `curl http://localhost:8000/metrics` showed live API and DB-backed gauge series including `saasguard_api_auth_failures_total`, `saasguard_export_jobs`, `saasguard_export_job_duration_avg_seconds`, `saasguard_queue_backlog_jobs`, `saasguard_oldest_pending_job_age_seconds`, and `saasguard_stale_processing_jobs`.
- `curl http://localhost:9101/metrics` showed live worker series including `saasguard_worker_jobs_started_total`, `saasguard_worker_jobs_failed_total`, `saasguard_worker_job_retries_total`, and `saasguard_worker_minio_upload_failures_total`.
- Prometheus instant queries confirmed the provisioned dashboard expressions resolve against live data for:
  - `Service Health / API Requests Per Minute`
  - `Service Health / Queue Backlog`
  - `Tenant Impact / Failed Exports By Tenant`
  - `Tenant Impact / Worker Retry and Failure Stages`
  - `Auth and Security / Token Validation Failures`
  - `Auth and Security / Cross-Tenant Job Access Denials`
- One cheap live auth event was generated with `GET /me` using an invalid bearer token. That produced a `401`, incremented `saasguard_api_auth_failures_total`, and emitted a Loki event with `event_name="auth.token_rejected"`.
- `Auth and Security / Authorization Denials` was patched to fall back to a labeled zero series when no `403` route labels have been emitted yet, which prevents a misleading permanent `No data` state on a quiet stack.
- `Auth and Security / Denied Event Volume (1h)` now groups denied Loki events by `event_name` instead of `keycloak_sub`. This matches the real local signal better because invalid-token rejections do not always carry a subject identifier.

## Metric Sources By Panel

- `Tenant Impact / Failed Exports By Tenant`
  Uses `saasguard_export_jobs{job="saasguard-api",status="failed"}`.
- `Tenant Impact / Completed Jobs By Tenant`
  Uses `saasguard_export_jobs{job="saasguard-api",status="completed"}`.
- `Tenant Impact / Export Requests By Tenant (24h)`
  Uses `increase(saasguard_api_export_requests_created_total{job="saasguard-api"}[24h])`.
- `Tenant Impact / Successful Export Latency By Tenant`
  Uses `saasguard_export_job_duration_avg_seconds{job="saasguard-api",status="completed"}`.
- `Tenant Impact / Affected Tenants Count`
  Uses `saasguard_export_jobs{job="saasguard-api",status=~"failed|retry_pending|queued"}` plus `saasguard_stale_processing_jobs{job="saasguard-api"}`.
- `Tenant Impact / Global Queue Pressure`
  Uses `saasguard_export_jobs{job="saasguard-api",status=...}` and `saasguard_oldest_pending_job_age_seconds{job="saasguard-api"}`.
- `Tenant Impact / Worker Retry and Failure Stages`
  Uses `increase(saasguard_worker_job_retries_total{job="saasguard-worker"}[5m])` and `increase(saasguard_worker_jobs_failed_total{job="saasguard-worker"}[5m])`, grouped by `failure_stage`.
- `Tenant Impact / Worker Dependency Failures`
  Uses `increase(saasguard_worker_minio_upload_failures_total{job="saasguard-worker"}[5m])` and `increase(saasguard_worker_db_query_failures_total{job="saasguard-worker"}[5m])`.
- `Service Health / Metrics Scrape Health`
  Uses `up{job=~"saasguard-api|saasguard-worker"}`.
- `Auth and Security / Token Validation Failures`
  Uses `saasguard_api_auth_failures_total`.
- `Auth and Security / Authorization Denials`
  Uses `saasguard_api_authorization_denials_total`.
- `Auth and Security / Cross-Tenant Job Access Denials`
  Uses `saasguard_api_job_read_denials_total`.
- `Auth and Security / Export Requests By Role`
  Uses `saasguard_api_export_requests_created_total`.
- `Auth and Security / Denied Event Volume (1h)`
  Uses Loki query `topk(10, sum by (event_name) (count_over_time({compose_service="api"} | json | outcome="denied" [1h])))`.
- `Auth and Security / Auth and Job Events`
  Uses Loki query `{compose_service="api"} | json | event_name=~"export.request_received|job.read_allowed|job.read_denied|auth.authorization_denied"`.
- `Auth and Security / Token Rejection Events`
  Uses Loki query `{compose_service="api"} | json | event_name="auth.token_rejected"`.
- `Auth and Security / Cross-Tenant Denial Events`
  Uses Loki query `{compose_service="api"} | json | event_name="job.read_denied"`.

## MinIO Outage Scenario

Scenario: MinIO outage

1. `docker compose stop minio`
2. Create an export from the frontend or call `POST /exports`.
3. Wait for the worker retry and eventual terminal failure.
4. Confirm Loki shows `worker.export.upload_failed` with message `object upload failed`.
5. Confirm Loki shows `worker.job_failed` with message `retry limit exceeded for transient failure`.
6. Confirm the Prometheus query `sum(increase(saasguard_worker_minio_upload_failures_total{job="saasguard-worker"}[5m]))` increases above `0`.
7. Confirm the `Tenant Impact / Worker Dependency Failures` panel shows MinIO upload failures `> 0`.
8. Confirm `Tenant Impact / Global Queue Pressure` and `Failed Exports By Tenant` reflect the pending or failed job state.
9. `docker compose start minio`
10. Create another export.
11. Confirm `saasguard_worker_minio_upload_failures_total` stops increasing and successful job completion/latency recover.

## How To Verify With Loki

- Open Grafana Explore against Loki.
- Query:
  - `{compose_service="api"} | json | event_name="auth.token_rejected"`
  - `{compose_service="api"} | json | event_name="export.request_received"`
  - `{compose_service="api"} | json | event_name=~"job.read_allowed|job.read_denied|auth.authorization_denied"`
- For worker-side outage verification in the current local stack, use the plain-text messages that are actually present in Celery logs:
  - `{compose_service="worker"} |= "object upload failed"`
  - `{compose_service="worker"} |= "retry limit exceeded for transient failure"`
  - `{compose_service="worker"} |= "transient job failure scheduled for retry"`
- Match the time range against the Grafana `Tenant Impact` panels and the worker failure counters in Prometheus.

## How To Verify With Prometheus

- Open Prometheus at `http://localhost:9090`.
- Check targets:
  - `up{job="saasguard-api"}`
  - `up{job="saasguard-worker"}`
- Check worker failure counters:
  - `sum(increase(saasguard_worker_minio_upload_failures_total{job="saasguard-worker"}[5m]))`
  - `sum by (failure_stage) (increase(saasguard_worker_job_retries_total{job="saasguard-worker"}[5m]))`
  - `sum by (failure_stage) (increase(saasguard_worker_jobs_failed_total{job="saasguard-worker"}[5m]))`
- Check DB-backed tenant state gauges:
  - `saasguard_export_jobs{job="saasguard-api"}`
  - `saasguard_export_job_duration_avg_seconds{job="saasguard-api",status="completed"}`
  - `saasguard_stale_processing_jobs{job="saasguard-api"}`

## Known Limitations

- The local worker now runs with Celery `--pool=solo` so Prometheus counters stay truthful in the same process that executes jobs. This is appropriate for the local demo stack, but a multi-process production worker would need Prometheus multiprocess support or a separate aggregation strategy.
- Worker failure verification in Loki currently relies on Celery-emitted plain-text log lines rather than structured `event_name` fields. The Grafana dashboards in this repo use Prometheus for worker failure trends and Loki only for API auth/event investigation.
- `Successful Export Latency By Tenant` only includes completed jobs. During a hard outage it can remain flat while failed and retry-pending panels rise.
- DB-backed gauges reflect current PostgreSQL state, not an append-only event history. They are intentionally paired with Loki and worker counters for incident timelines.
