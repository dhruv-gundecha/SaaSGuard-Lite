# Metrics Required for OE Dashboard

These metrics are already emitted or logically derived from the system.

## API Performance
- saasguard_api_request_latency_seconds
- saasguard_api_request_latency_seconds_count
- http_5xx_total
- http_4xx_total

## Authentication
- saasguard_api_auth_failures_total
- token_validation_failures_total

## Authorization
- tenant_access_denied_total

## Async Jobs
- jobs_created_total
- jobs_completed_total
- jobs_failed_total
- job_processing_latency_seconds

## Availability (via Uptime Kuma)
- API availability
- frontend availability
- Keycloak availability
- Postgres (TCP)
- Redis (TCP)
- MinIO health

## Observability Stack
- grafana availability
- prometheus availability