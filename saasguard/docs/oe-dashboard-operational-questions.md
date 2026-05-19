# OE Dashboard Operational Questions

The Operations Overview page inside SaaSGuard-Lite is not a replacement for Grafana, Loki, Prometheus, or Uptime Kuma. Its job is to answer the first operational question quickly, show likely business impact, and route the operator to the right detailed tool.

Access to this page is intentionally restricted to internal `soc_admin` or `ops_admin` users. Grafana, Loki, Prometheus, and Uptime Kuma are global observability systems and may contain cross-tenant operational data. Tenant admins should receive tenant-scoped product, status, and audit views instead of raw access to global observability links.

## Dashboard Verification Notes

- The provisioned dashboards were verified against live product behavior rather than only against metric names in code.
- Loki logs and Prometheus metrics can diverge when the app logs a failure but does not increment a corresponding metric. This observability pass closed that gap for MinIO upload failures and worker failure-stage counters.
- `Tenant Impact` now combines live worker counters with PostgreSQL-backed gauges so operators can see truthful failed, retry-pending, queued, stale-processing, and successful-latency signals even when seeded demo data exists before new jobs are run.
- `Auth and Security` was rechecked against the current local stack on `2026-05-18`. The authorization-denial panel now falls back to a labeled zero series when no `403` route labels exist yet, and the denied-event volume panel now groups by `event_name` so invalid-token bursts still appear even when no subject is known.

## 1. Is the application healthy and available?

- **Primary source:** Product Operations Overview page, backed by `GET /operations/summary`
- **Detailed source:** Grafana `Service Health`, Uptime Kuma
- **Why it matters:** if the API or frontend is down, customers cannot log in, request exports, inspect jobs, or download results.
- **How to investigate:** start on the Operations page, then open `Service Health` for API 5xx and latency trends, and Uptime Kuma for edge/service availability.
- **Remaining gap:** the product page currently summarizes API health better than frontend-specific health; Uptime Kuma still remains the better frontend outage detector.

## 2. Are users experiencing high latency before a full outage?

- **Primary source:** Operations Overview API section
- **Detailed source:** Grafana `Service Health`
- **Why it matters:** latency spikes are often the first signal of overload, bad releases, or failing dependencies. Customers abandon export requests before the system is fully down.
- **How to investigate:** compare API p95 latency with API 5xx rate and request volume. If dependencies are still healthy, treat it as a possible application regression.
- **Remaining gap:** p99 latency is not yet surfaced in the product page and alert thresholds still live mainly in documentation rather than automated alert rules.

## 3. Are exports being processed correctly?

- **Primary source:** Operations Overview export pipeline section
- **Detailed source:** Grafana `Tenant Impact`
- **Why it matters:** SaaSGuard-Lite’s core product value is reliable tenant-scoped export completion. If jobs are accepted but not completed, customers experience a broken product even if login still works.
- **How to investigate:** inspect queued, retry-pending, processing, completed-last-hour, failed-last-hour, and oldest pending job age. Then pivot to `Tenant Impact` to see worker failures and queue pressure over time.
- **Remaining gap:** the product page currently summarizes global pipeline state; it does not yet break queue pressure down by incident cohort or recent deployment.

## 4. Are jobs stuck in queue or retry loops?

- **Primary source:** Operations Overview export and worker sections
- **Detailed source:** Grafana `Tenant Impact`, Prometheus
- **Why it matters:** backlog growth and retries are direct business-risk signals because customers stop receiving exports on time.
- **How to investigate:** look at queued plus retry-pending counts, oldest pending job age, worker retry count, and recent failed jobs. If Redis, PostgreSQL, and MinIO are healthy, suspect worker code or release instability.
- **Remaining gap:** there is still no dedicated product-side explanation of whether a retry wave is transient or persistent; operators still need Grafana for that history.

## 5. Is the worker healthy?

- **Primary source:** Operations Overview worker section
- **Detailed source:** Grafana `Tenant Impact`, Loki
- **Why it matters:** the API can continue accepting jobs while the worker silently fails, creating a customer-visible reliability issue without an obvious login outage.
- **How to investigate:** compare worker started/completed/failed totals with queue pressure. If MinIO upload failures or DB query failures are rising, move to Loki and the worker dependency panels.
- **Remaining gap:** worker liveness is inferred from behavior and counters, not from a dedicated worker heartbeat metric.

## 6. Are authorization denials increasing?

- **Primary source:** Operations Overview security section
- **Detailed source:** Grafana `Auth and Security`, Loki
- **Why it matters:** rising denials can indicate role drift, broken membership logic, or malicious probing. All of those affect customer trust and support load.
- **How to investigate:** compare auth failures, authorization denials, and cross-tenant denials. Open the auth dashboard, then inspect Loki for `auth.token_rejected`, `auth.authorization_denied`, and `job.read_denied`.
- **Dashboard note:** denied-event volume is intentionally grouped by event type rather than by subject because some rejected tokens have no resolved subject identifier.
- **Remaining gap:** the product page shows current signals but not actor-level grouping or long-term baselines; Grafana and Loki remain necessary for pattern analysis.

## 7. Is there evidence of possible cross-tenant access attempts?

- **Primary source:** Operations Overview security section
- **Detailed source:** Grafana `Auth and Security`, Loki
- **Why it matters:** tenant isolation is the top product priority. Even denied cross-tenant attempts matter because they may indicate probing, test regressions, or a real incident precursor.
- **How to investigate:** check cross-tenant denial counts first. Then pivot to Loki with `event_name="job.read_denied"` and confirm the denial path is behaving as expected.
- **Remaining gap:** the page can show denied attempts, but it cannot prove there has been no exposure. Automated isolation tests and code review remain part of the control set.

## 8. Did a recent deployment introduce instability?

- **Primary source:** Operations Overview deployment/release indicator
- **Detailed source:** Grafana `Service Health`, Loki
- **Why it matters:** release regressions are a business continuity issue because they create sudden outages, latency spikes, or broken export behavior despite healthy infrastructure.
- **How to investigate:** if the deployment indicator is degraded or unhealthy while PostgreSQL, Redis, MinIO, and Keycloak all look healthy, inspect recent API/worker logs and compare with the latest release change.
- **Remaining gap:** the product currently uses a heuristic regression signal. It does not yet ingest explicit deployment metadata or release timestamps.

## 9. Are dependencies healthy?

- **Primary source:** Operations Overview dependency section
- **Detailed source:** Uptime Kuma, Prometheus targets, MinIO console
- **Why it matters:** PostgreSQL, Redis, MinIO, and Keycloak are all on the critical path for secure export processing. Dependency failures quickly translate into broken auth, stuck queues, or failed downloads.
- **How to investigate:** use the product page for bounded health checks and latency, then open Uptime Kuma or the relevant tool for a deeper view.
- **Remaining gap:** the product page performs point-in-time checks only. It does not yet show dependency flapping history or multi-check rollups.

## 10. Are logs and metrics sufficient for incident investigation?

- **Primary source:** Operations Overview investigation shortcuts
- **Detailed source:** Grafana, Loki, Prometheus
- **Why it matters:** weak observability turns small failures into prolonged incidents because operators cannot confirm scope, cause, or customer impact quickly.
- **How to investigate:** use the page as a router. If the problem is metric-shaped, go to Grafana or Prometheus. If the problem is event-shaped, go to Loki Explore.
- **Remaining gap:** the product page currently links operators to the right tools, but it does not yet embed recent log excerpts or target status details.

## Remaining Observability Gaps

- The Operations page does not yet surface frontend-specific latency or browser error telemetry.
- Release/regression detection is heuristic and not tied to explicit deployment markers.
- The summary uses bounded dependency checks, but not all of those checks have historical alerting wired into Grafana or Prometheus yet.
- Worker health is inferred from totals and job outcomes rather than a heartbeat or last-seen processing timestamp.
- Cross-tenant denial visibility is useful, but absence of denials is not proof of safety. Automated tenant-isolation tests remain a critical control.
