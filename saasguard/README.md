# SaaSGuard-Lite

SaaSGuard-Lite is a developer-realistic secure-by-design multi-tenant export service with:

- FastAPI API
- React + Vite frontend console
- Celery worker
- PostgreSQL as the authoritative system of record
- Redis as a transport-only queue
- MinIO object storage
- Keycloak for OIDC authentication
- Prometheus, Loki, Promtail, and Grafana for observability

## Security model

- Keycloak authenticates identity with bearer JWTs.
- The application authorizes tenant membership and role access.
- Redis carries only `job_id`.
- The worker reloads trusted job and tenant context from PostgreSQL before doing work.
- The worker never trusts queue payloads for tenant identity or user identity.
- Audit events are written to PostgreSQL for key security-relevant actions.
- Logs are structured JSON and avoid secrets, raw JWTs, passwords, and CSV contents.

## Roles

- `viewer`: read jobs and download completed exports
- `analyst`: viewer permissions plus create export jobs
- `tenant_admin`: analyst permissions plus tenant audit access

## Development users

Keycloak realm import and the local demo seed bootstrap align these users:

- `alice` / `alice-password` -> `tenant_alpha` -> `analyst`
- `bob` / `bob-password` -> `tenant_beta` -> `analyst`
- `carol` / `carol-password` -> `tenant_alpha`, `tenant_beta` -> `tenant_admin`

The backend keeps production-style `sub` matching by default. In local mode only, `DEV_AUTH_USERNAME_FALLBACK_ENABLED=true` allows the app to repair a seeded internal user mapping from `preferred_username` if the imported Keycloak user UUIDs drift.

## Run locally

1. Refresh the environment file:

```bash
cp .env.example .env
cp frontend/.env.example frontend/.env
```

2. Add the canonical local Keycloak hostname to your hosts file:

```text
127.0.0.1 auth.saasguard.local
```

This project intentionally uses `http://auth.saasguard.local:8081` as the only local Keycloak base URL. Port `8080` on the host is already occupied in this environment, so `8081` is the public Keycloak port by design.

3. If you previously ran the older mock-auth version, remove the old database volume so the new Keycloak database and migrations can initialize cleanly:

```bash
docker compose down -v
```

4. Start the full stack:

```bash
docker compose up --build
```

On local startup the API uses a FastAPI lifespan bootstrap: it waits for the database connection, loads and applies SQL migrations from `/app/sql/migrations` inside the container, verifies the required tables exist, then runs the idempotent demo seed, and only then begins serving requests.

5. Rerun the demo seed without resetting the stack:

```bash
docker compose exec api python -m src.seed_dev_data
```

6. Reset to a clean environment and reseed from scratch:

```bash
docker compose down -v
docker compose up --build
```

When you change `keycloak/realm-export.json`, restart Keycloak with `docker compose down -v` before `docker compose up --build`. The Keycloak import runs only when the realm database is initialized, so existing realm state can mask hostname, client, and mapper fixes.

If you want to run the frontend outside Docker during UI development:

```bash
cd frontend
npm install
npm run dev
```

## CI/CD

Local test command:

```bash
docker compose run --rm -v "$PWD:/app" api pytest -v
```

GitHub Actions runs the same pytest suite inside the API container on every push and pull request.

Operational risk deliverables added in this repo include:

- [docs/customer-disruption-risks.md](/home/darthdg/saasguard/docs/customer-disruption-risks.md) for the highest customer-impacting disruption scenarios
- [docs/manual-tests-and-missing-alerts.md](/home/darthdg/saasguard/docs/manual-tests-and-missing-alerts.md) for manual drills and remaining OE alert coverage gaps
- risk-focused pytest coverage for health, auth-failure signaling, queue payload trust boundaries, cross-tenant access denial, and safe worker failure handling

The current automated tests validate:

- functional export creation through `POST /exports`
- cross-tenant authorization denial for `GET /jobs/{job_id}`
- worker reconstruction of authoritative job context from the database before export processing

## Local endpoints

- API: `http://localhost:8000`
- Frontend: `http://localhost:3001`
- Keycloak: `http://auth.saasguard.local:8081`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`
- Uptime Kuma: `http://localhost:3002`
- Worker metrics: `http://localhost:9101`

Grafana defaults:

- user: `admin`
- password: `admin`

## Get a bearer token

Use the Keycloak token endpoint with the seeded API client:

```bash
curl -s \
  -X POST http://auth.saasguard.local:8081/realms/saasguard/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=saasguard-api" \
  -d "client_secret=saasguard-dev-secret" \
  -d "username=alice" \
  -d "password=alice-password"
```

Extract `access_token` from the JSON response and set it:

```bash
export ACCESS_TOKEN='<token>'
```

## Exercise the API

Create an export as `alice`:

```bash
curl -X POST http://localhost:8000/exports \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Read a job:

```bash
curl http://localhost:8000/jobs/<job_id> \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Download a completed export:

```bash
curl http://localhost:8000/jobs/<job_id>/download \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

For multi-tenant users like `carol`, set the active tenant explicitly:

```bash
curl -X POST http://localhost:8000/exports \
  -H "Authorization: Bearer $CAROL_TOKEN" \
  -H "X-Active-Tenant: tenant_alpha"
```

## Seeded demo data

The local demo seed creates:

- tenants: `tenant_alpha`, `tenant_beta`
- memberships:
  - `alice` -> `tenant_alpha` -> `analyst`
  - `bob` -> `tenant_beta` -> `analyst`
  - `carol` -> `tenant_alpha` -> `tenant_admin`
  - `carol` -> `tenant_beta` -> `tenant_admin`
- tenant records for both tenants so exported CSVs and the dashboard have realistic content
- job history with stable IDs so reseeding does not create duplicates

Expected job history after seeding:

- `tenant_alpha`: 2 completed jobs and 1 queued job
- `tenant_beta`: 2 completed jobs, 1 failed job, and 1 processing job
- failed job example: `MinIO upload failed after 2 retries: PutObject to bucket exports returned HTTP 503 Service Unavailable`

Completed jobs use realistic object keys such as:

- `exports/tenant_alpha/2026/04/alpha-cost-rollup-20260418T091500Z.csv`
- `exports/tenant_beta/2026/04/beta-usage-20260419T041200Z.csv`

## Use the frontend

1. Open `http://localhost:3001`.
2. Click `Sign in with Keycloak`.
3. Log in as `alice`, `bob`, or `carol`.
4. If the user has multiple memberships, choose an active tenant in the top bar.
5. Use:
   - `Dashboard` for identity and tenant context
   - `Exports` to request a new export
   - `Jobs` to inspect tenant-scoped jobs and failures
   - `Audit` to review audit evidence when the role allows it
   - `Operations` to jump into Grafana, Prometheus, and Loki-oriented workflows

Frontend notes:

- The browser UI uses Keycloak PKCE and keeps tokens in the adapter memory rather than storing them in local storage.
- The frontend sends `X-Active-Tenant` only for authorized memberships selected in the UI.
- The backend remains the source of truth for authorization decisions.

## Observability

Prometheus scrapes:

- `api:8000/metrics`
- `worker:9101`

Promtail ships container stdout logs to Loki. The application emits structured JSON fields including:

- `timestamp`
- `level`
- `service`
- `environment`
- `event_name`
- `correlation_id`
- `request_id`
- `job_id`
- `tenant_id`
- `user_id`
- `keycloak_sub`
- `outcome`
- `error_type`
- `error_message`

Starter Grafana dashboards are provisioned automatically:

- `Service Health`
- `Tenant Impact`
- `Auth and Security`

## Uptime Kuma

Uptime Kuma is included in the local Compose stack as the lightweight uptime monitor for the developer environment and incident drills.

The stack uses the `louislam/uptime-kuma:2-slim` image. The current Uptime Kuma Docker tag guidance recommends the `2` or `2-slim` major-version tags for v2 and explicitly deprecates `latest`, so this local stack stays on the supported slim v2 track without pulling in the heavier full image.

Start the full stack, including Uptime Kuma:

```bash
docker compose up --build
```

If the rest of the stack is already running and you only need Kuma:

```bash
docker compose up -d uptime-kuma
```

Open the UI at `http://localhost:3002`.

First-run expectations:

- On first boot, create the initial Uptime Kuma admin account in the web UI.
- Uptime Kuma stores its state in the named Docker volume `uptime_kuma_data`.
- The frontend already uses host port `3001`, so Uptime Kuma is published on `3002` to avoid a collision.
- The container keeps using internal port `3001`; only the host-facing port changes.
- The Compose service includes a container-local HTTP healthcheck so `docker compose ps` can show whether Kuma itself is ready.

Recommended update flow:

```bash
docker compose pull uptime-kuma
docker compose up -d --force-recreate uptime-kuma
```

Reset only Uptime Kuma data:

```bash
docker compose stop uptime-kuma
docker volume rm saasguard_uptime_kuma_data
docker compose up -d uptime-kuma
```

Recommended monitors for this project:

- API health: `HTTP(s)` monitor to `http://api:8000/health`
  Why: checks the FastAPI process and basic app boot path without requiring auth.
- Frontend UI: `HTTP(s)` monitor to `http://frontend:3001/`
  Why: verifies the Vite dev server is serving the console.
- Keycloak discovery: `HTTP(s) JSON Query` monitor to `http://auth.saasguard.local:8081/realms/saasguard/.well-known/openid-configuration`
  Query: `$.issuer`
  Expected value: `http://auth.saasguard.local:8081/realms/saasguard`
  Why: verifies both Keycloak reachability and the canonical issuer contract.
- Grafana API: `HTTP(s) JSON Query` monitor to `http://grafana:3000/api/health`
  Query: `$.database`
  Expected value: `ok`
  Why: checks Grafana beyond the login page.
- Prometheus health: `HTTP(s)` monitor to `http://prometheus:9090/-/healthy`
  Why: confirms Prometheus is live and serving its own health endpoint.
- MinIO API health: `HTTP(s)` monitor to `http://minio:9000/minio/health/live`
  Why: checks object storage directly instead of only the console UI.
- MinIO console: `HTTP(s)` monitor to `http://minio:9001/`
  Why: confirms the operator-facing console is reachable.
- Worker metrics endpoint: `HTTP(s) Keyword` monitor to `http://worker:9101/metrics`
  Keyword: `worker_jobs_processed_total`
  Why: confirms the Celery worker metrics server is alive.
- PostgreSQL: `TCP Port` monitor to `postgres:5432`
  Why: detects database reachability separately from application health.
- Redis: `TCP Port` monitor to `redis:6379`
  Why: detects queue transport reachability directly.

Monitor design guidance:

- Prefer internal Docker-network targets such as `api`, `frontend`, `prometheus`, and `postgres` for stack-health monitors. This checks the actual service-to-service paths inside Compose.
- Use the canonical hostname `auth.saasguard.local` for the Keycloak monitor because issuer correctness is part of the identity contract, not just process uptime.
- Use host-published URLs only when you explicitly want to test the developer-facing entrypoint from outside Docker.
- A practical incident-response split is to use internal targets for dependency and service health, then add a small number of host-URL checks such as `http://localhost:3001` and `http://localhost:3002` for developer-facing entrypoints.
- Uptime Kuma does not ship these monitors preloaded in this repository; create them once in the UI after first boot using the targets above.

## Data model highlights

- `users`: internal application users keyed by `keycloak_sub`
- `tenants`: tenant registry
- `memberships`: authoritative tenant-role mapping
- `export_jobs`: authoritative async job context including `tenant_id`, requester, role snapshot, correlation ID, retries, and timestamps
- `audit_events`: durable evidence for security-sensitive actions

## Demo seed behavior

- Automatic local seeding is controlled by `DEV_SEED_ENABLED` and defaults to `true` when `APP_ENV=local`.
- Manual reseeding uses `python -m src.seed_dev_data`.
- API bootstrap order is: database available -> migrations applied -> dev seed runs -> API serves requests.
- The API and worker images both include the `sql/` directory so local startup does not depend on Docker volume init scripts for application schema creation.
- The seed is idempotent and updates fixed demo rows instead of inserting duplicates.
- Production behavior is unchanged unless you explicitly enable dev-only flags outside local mode.

## Async authorization model

1. API validates the bearer token against Keycloak JWKS.
2. API maps `sub` to an internal user and active tenant membership.
3. API performs role checks in application code.
4. API writes the job to PostgreSQL with authoritative tenant and requester context.
5. API sends only `job_id` to Redis.
6. Worker receives `job_id`, reloads the job from PostgreSQL, claims it atomically, and reconstructs trusted context from the database.
7. Worker queries tenant-scoped data using `tenant_id` from the job record.
8. Worker persists state transitions, retries transient failures only, and records audit/log evidence.

## Files

- Frontend app: [frontend/src](/home/darthdg/saasguard/frontend/src)
- API: [src/api.py](/home/darthdg/saasguard/src/api.py)
- Authn/Authz: [src/auth.py](/home/darthdg/saasguard/src/auth.py), [src/authz.py](/home/darthdg/saasguard/src/authz.py)
- Worker task: [src/tasks.py](/home/darthdg/saasguard/src/tasks.py)
- Database access: [src/db.py](/home/darthdg/saasguard/src/db.py)
- Dev seed bootstrap: [src/seed_dev_data.py](/home/darthdg/saasguard/src/seed_dev_data.py)
- Migrations: [sql/migrations/001_core_schema.sql](/home/darthdg/saasguard/sql/migrations/001_core_schema.sql), [sql/migrations/002_export_jobs_and_audit.sql](/home/darthdg/saasguard/sql/migrations/002_export_jobs_and_audit.sql), [sql/migrations/003_tenant_record_uniqueness.sql](/home/darthdg/saasguard/sql/migrations/003_tenant_record_uniqueness.sql)
- Keycloak realm import: [keycloak/realm-export.json](/home/darthdg/saasguard/keycloak/realm-export.json)
- Frontend env example: [frontend/.env.example](/home/darthdg/saasguard/frontend/.env.example)
- Observability config: [observability/prometheus/prometheus.yml](/home/darthdg/saasguard/observability/prometheus/prometheus.yml), [observability/promtail/config.yml](/home/darthdg/saasguard/observability/promtail/config.yml)
- Architecture notes: [docs/architecture.md](/home/darthdg/saasguard/docs/architecture.md)
- Incident runbook: [docs/incident-runbook.md](/home/darthdg/saasguard/docs/incident-runbook.md)

## Automated tests

Run the automated tests with:

```bash
docker compose run --rm -v "$PWD:/app" api pytest -v
```

Run that command from inside the `saasguard/` directory.
