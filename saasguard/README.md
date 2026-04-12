# SaaSGuard-Lite

Minimal containerized export service with:

- FastAPI API
- Celery worker
- Redis broker
- PostgreSQL for authoritative job state and tenant data
- MinIO for CSV object storage

## What it does

- Uses temporary header auth with `X-User`
- Maps users to tenants in code
- Writes the export job to PostgreSQL before enqueueing
- Sends only `job_id` through the queue
- Worker reloads the job from PostgreSQL and exports only that job's tenant rows
- Stores the generated CSV in MinIO

Hardcoded users:

- `alice` -> `tenant_alpha`
- `bob` -> `tenant_beta`

## Run locally

1. Copy the environment file:

```bash
cp .env.example .env
```

2. Start the stack:

```bash
docker compose up --build
```

3. Create an export for `alice`:

```bash
curl -X POST http://localhost:8000/exports -H "X-User: alice"
```

4. Inspect the job:

```bash
curl http://localhost:8000/jobs/<job_id> -H "X-User: alice"
```

5. Inspect MinIO:

- API: `http://localhost:9000`
- Console: `http://localhost:9001`
- Default credentials come from `.env`

The exported object key will look like:

```text
exports/tenant_alpha/<job_id>.csv
```

## Notes

- The PostgreSQL init script at [`sql/init.sql`](/home/darthdg/saasguard/sql/init.sql) creates the schema and multi-tenant sample rows.
- API code is in [`src/api.py`](/home/darthdg/saasguard/src/api.py).
- Worker task code is in [`src/tasks.py`](/home/darthdg/saasguard/src/tasks.py).
