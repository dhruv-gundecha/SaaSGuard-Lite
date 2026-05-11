# Manual Tests and Missing Alerts

## Manual Tests Not Yet Automated

### Full browser login through Keycloak PKCE

- **Why it matters:** this is the real customer entry path, and it exercises frontend redirect handling, Keycloak session state, token issuance, and API token acceptance together.
- **Why not automated yet:** the current pytest suite is API-focused and deterministic; it does not run a browser, PKCE redirect flow, or a full Keycloak UI interaction.
- **How to test manually:** open `http://localhost:3001`, click `Sign in with Keycloak`, log in as `alice`, `bob`, and `carol`, confirm the app lands on an authenticated page, and verify `/me` returns the expected identity and memberships.
- **Desired future automation:** Playwright-based browser test with local Keycloak seeded credentials and a deterministic callback assertion.

### Multi-tenant active tenant switching as Carol

- **Why it matters:** `carol` is the best check that frontend tenant switching and backend `X-Active-Tenant` authorization stay aligned for a multi-membership user.
- **Why not automated yet:** it requires browser state, tenant switch UI handling, and assertions across multiple authenticated pages.
- **How to test manually:** sign in as `carol`, switch between `tenant_alpha` and `tenant_beta`, create an export in each tenant, then confirm job lists and audit views stay tenant-scoped after each switch.
- **Desired future automation:** end-to-end browser test that changes active tenant and validates tenant-scoped API responses and rendered job rows.

### Uptime Kuma monitor behavior during container shutdown

- **Why it matters:** SaaSGuard-Lite currently relies on Uptime Kuma to tell operators when frontend, API, or Keycloak paths are down before customers report it.
- **Why not automated yet:** it requires orchestrating real container failure and asserting monitor transitions in a separate tool UI.
- **How to test manually:** stop `frontend` or `api` with `docker compose stop frontend` or `docker compose stop api`, watch Uptime Kuma at `http://localhost:3002`, and confirm the related monitor turns `Down` quickly enough to be actionable.
- **Desired future automation:** scripted incident drill that shuts down one service, polls Uptime Kuma API, and restores the service.

### Full export download through frontend

- **Why it matters:** the core promise is not just job creation but a successful tenant-scoped CSV download from the UI.
- **Why not automated yet:** current tests stop at API and worker boundaries and do not validate browser download handling or presigned URL behavior from the frontend.
- **How to test manually:** sign in as `alice`, request an export, wait for completion in the jobs page, click download, and verify the CSV contents belong only to `tenant_alpha`.
- **Desired future automation:** Playwright download test with fixture CSV validation and tenant-content assertions.

### MinIO credential or bucket misconfiguration drill

- **Why it matters:** storage failures are one of the fastest ways to convert accepted export jobs into stuck or failed customer-visible work.
- **Why not automated yet:** the unit-style test suite can simulate upload failure, but it does not currently reconfigure a live MinIO dependency and validate the full operator recovery path.
- **How to test manually:** change MinIO credentials or bucket name in `.env`, restart the stack, submit an export, confirm worker upload failures and job retries/failures, then restore correct settings and verify a new export completes.
- **Desired future automation:** compose-level failure scenario in CI or nightly smoke tests that injects bad storage config and validates recovery.

### DDoS or load spike against `POST /exports`

- **Why it matters:** bursty export creation can degrade availability for legitimate users even if authorization is technically correct.
- **Why not automated yet:** meaningful load testing needs concurrency, rate shaping, and environment isolation that do not fit the current deterministic container pytest job.
- **How to test manually:** run a controlled load tool against `POST /exports` using a seeded authenticated user, watch API request rate, queue backlog, oldest pending age, and worker completion rate in Grafana, then verify the system recovers after load stops.
- **Desired future automation:** dedicated k6 or Locust scenario in a non-PR environment with threshold-based assertions.

### Recovery after Redis, PostgreSQL, or MinIO restart

- **Why it matters:** customers care about whether the service recovers cleanly after dependency interruption, not just whether a happy-path request works on a fresh stack.
- **Why not automated yet:** restart and recovery timing can be noisy in shared CI and would require longer-running orchestration assertions.
- **How to test manually:** start the stack, create one or more exports, restart `redis`, `postgres`, or `minio` individually with `docker compose restart <service>`, then confirm whether new exports succeed and backlog drains after recovery.
- **Desired future automation:** scheduled compose recovery suite with dependency restart orchestration and post-recovery synthetic export checks.

### Verifying Grafana dashboard panels during real incidents

- **Why it matters:** an alerting metric is only useful if operators can interpret the dashboard quickly during failure conditions.
- **Why not automated yet:** panel usefulness and incident clarity are not well-captured by unit tests.
- **How to test manually:** trigger representative failures such as worker stop, Keycloak outage, or MinIO upload failure, and verify the `Service Health`, `Auth and Security`, and `Tenant Impact` dashboards show the expected signal within one scrape interval.
- **Desired future automation:** dashboard smoke tests for query validity plus scripted incident drills that assert data appears in target panels.

## Proactive Alert Metrics Not Yet in OE Dashboard

This section is a coverage tracker, not a claim that every item is missing from code. Some metrics are already instrumented but still need better alert thresholds or dedicated panels.

| Metric or signal | Why it matters | Suggested threshold | Current status |
| --- | --- | --- | --- |
| API 5xx alert | Detects API outages and dependency failures before customers fully lose the workflow. | `> 2%` 5xx ratio for 5 minutes or any sustained spike after deploy. | `implemented` |
| Request latency p95/p99 | Detects brownouts before hard failure, especially during export bursts or downstream slowness. | `p95 > 1s` for 10 minutes, `p99 > 3s` for 5 minutes. | `partially implemented` |
| Auth failure spike | Detects Keycloak outage, issuer drift, or bad client configuration quickly. | `> 5/min` sustained for 5 minutes in local/demo, tune higher in real envs. | `implemented` |
| Authorization denial spike | Detects broken membership logic or probing of protected resources. | `> 10 denials/5m` or sudden deviation from baseline. | `implemented` |
| Export request spike | Detects DDoS or abuse of `POST /exports` before backlog becomes severe. | `> 3x` baseline export request rate for 5 minutes. | `implemented` |
| Queue backlog threshold | Detects worker saturation and stuck demand. | `queued_jobs > 20` for 10 minutes in the demo environment. | `implemented` |
| Oldest pending job age threshold | Detects customer-visible wait time regression more directly than backlog count alone. | `oldest_pending_job_age_seconds > 300` for 10 minutes. | `implemented` |
| Worker failure or retry spike | Detects degraded processing even when jobs are still starting. | `failed + retries > 5/10m` or any sustained retry wave at the same failure stage. | `implemented` |
| DB query failure spike | Detects loss of authoritative state access in the worker path. | `> 1/min` for 5 minutes. | `implemented` |
| MinIO upload failure spike | Detects object storage disruption that directly blocks completed exports. | `> 1/min` for 5 minutes. | `implemented` |
| No completed jobs in recent window | Detects silent worker stalls where requests continue but nothing finishes. | `0 completions for 15 minutes` while export requests continue. | `not yet implemented` |
| Uptime Kuma monitor failure aggregation | Gives a single incident-level view when multiple customer-facing monitors fail together. | Any customer-facing monitor down for `> 2` consecutive checks, escalate when more than one fails. | `not yet implemented` |

### PromQL or signal references for items still needing stronger OE treatment

- API latency p95:

```promql
histogram_quantile(
  0.95,
  sum by (le) (rate(saasguard_api_request_latency_seconds_bucket[5m]))
)
```

- API latency p99:

```promql
histogram_quantile(
  0.99,
  sum by (le) (rate(saasguard_api_request_latency_seconds_bucket[5m]))
)
```

- No completed jobs while requests continue:

```promql
sum(increase(saasguard_worker_jobs_completed_total[15m])) == 0
and
sum(increase(saasguard_api_export_requests_created_total[15m])) > 0
```

- Uptime Kuma aggregation:
  This is not yet sourced from Prometheus in the current repo. It still needs either a Prometheus exporter path or a dedicated dashboard/API integration.
