# OE Dashboard Verification

This document records the current Operational Excellence dashboard surfaces that are actually present in the repository and how they are meant to be verified.

## Current Dashboard Set

Provisioned Grafana dashboards:

- `Service Health`
- `Tenant Impact`
- `Auth and Security`

Supporting operator surfaces:

- frontend `Operations` page
- Prometheus
- Loki through Grafana Explore
- Uptime Kuma

## What the Current Dashboards Cover

### Service Health

- API requests per minute
- API error rate
- auth failure rate
- worker throughput
- queue backlog
- dependency failures
- export request rate
- worker failures and retries
- API latency and queue-wait p95
- Prometheus scrape health

### Tenant Impact

- failed exports by tenant
- completed jobs by tenant
- export requests by tenant
- successful export latency by tenant
- affected tenant count
- top tenants by job volume
- global queue pressure
- worker retry and failure stages
- worker dependency failures
- metrics scrape health

### Auth and Security

- token validation failures
- authorization denials
- cross-tenant job access denials
- export requests by role
- denied event volume from Loki
- auth and job event logs
- token rejection logs
- cross-tenant denial logs

## Operations Page Coverage

The frontend `Operations` page currently summarizes:

- API health
- export pipeline state
- worker health
- security and authorization signals
- dependency health
- release or regression suspicion
- investigation shortcuts into Grafana, Prometheus, Loki, Uptime Kuma, and MinIO

Access is intentionally restricted to internal operations roles.

## How to Verify

### Static repository verification

- confirm dashboard JSON files exist in `observability/grafana/dashboards/`
- confirm provisioning config exists in `observability/grafana/provisioning/`
- confirm Prometheus datasource and Loki datasource provisioning

### Live stack verification

1. Start the Compose stack.
2. Open Grafana.
3. Confirm the three dashboards are provisioned.
4. Visit the frontend `Operations` page as `soc`.
5. Confirm the page links to the expected external tools and renders summary sections.

### Metrics verification

Current high-value metrics to verify:

- `saasguard_api_auth_failures_total`
- `saasguard_api_authorization_denials_total`
- `saasguard_api_job_read_denials_total`
- `saasguard_export_jobs`
- `saasguard_oldest_pending_job_age_seconds`
- `saasguard_stale_processing_jobs`
- `saasguard_worker_jobs_started_total`
- `saasguard_worker_jobs_failed_total`
- `saasguard_worker_job_retries_total`
- `saasguard_worker_minio_upload_failures_total`

### Log verification

Current high-value Loki queries:

- `{compose_service="api"} | json | event_name="auth.token_rejected"`
- `{compose_service="api"} | json | event_name="job.read_denied"`
- `{compose_service="worker"} | json | event_name="worker.job_failed"`

## Known Limitations

- the repository now commits alert-rule definitions, but the thresholds are intentionally local/demo tuned rather than production tuned
- Uptime Kuma monitor definitions are not exported as a repository artifact
- worker-side Loki usefulness is strongest when structured worker event names remain present; some earlier docs relied on plain-text Celery output patterns

## Alerting

Alert provisioning files:

- `observability/grafana/provisioning/alerting/saasguard-alert-rules.yml`
- `observability/grafana/provisioning/alerting/saasguard-notifications.yml`

These thresholds are intentionally tuned for a local/demo environment and should be raised or otherwise re-tuned for production.

| Alert name | Signal | Threshold | Severity | Related runbook section | How to test locally |
| --- | --- | --- | --- | --- | --- |
| SaaSGuard Authentication Failure Spike | `saasguard_api_auth_failures_total` | `increase(...[5m]) > 10` for `2m` | Critical | `docs/incident-runbook.md#token-validation-failure-spike` | induce invalid or wrong-issuer bearer tokens and confirm Grafana Alerting shows the rule firing |
| SaaSGuard Authorization Denial Spike | `saasguard_api_authorization_denials_total` | `increase(...[5m]) > 10` for `2m` | High | `docs/incident-runbook.md#authorization-denial-spike` | repeatedly call protected endpoints with the wrong tenant or insufficient role |
| SaaSGuard Export Failure Spike | `saasguard_worker_jobs_failed_total` | `increase(...[5m]) > 2` for `5m` | Critical | `docs/incident-runbook.md#worker-failure-spike` | induce worker-side failure such as storage or DB disruption and watch failed-job volume rise in Grafana Alerting |
| SaaSGuard Queue Backlog Growth | `saasguard_export_jobs{status="queued"}` or `saasguard_oldest_pending_job_age_seconds` | queued jobs `> 5` or oldest pending age `> 7200s` for `5m` | High | `docs/incident-runbook.md#queue-backlog-growth` | stop or break the worker, create exports, and observe queue depth or oldest-age growth |
| SaaSGuard Worker Failure or Retry Spike | `saasguard_worker_jobs_failed_total` plus `saasguard_worker_job_retries_total` | combined 10-minute increase greater than `5` for `5m` | High | `docs/incident-runbook.md#worker-failure-spike` | induce repeated transient worker failures and confirm retries/failures accumulate |
| SaaSGuard MinIO Upload Failure Spike | `saasguard_worker_minio_upload_failures_total` | `increase(...[5m]) > 1` for `5m` | Critical | `docs/incident-runbook.md#minio-outage` | stop MinIO or break MinIO credentials/bucket config and request exports |

Current local-demo notification model:

- alerts are provisioned with a placeholder local-demo contact point
- no real webhook, Slack, PagerDuty, or email secrets are committed
- operators should review alert state in the Grafana Alerting UI during local validation
