#!/usr/bin/env bash
set -euo pipefail

DOCKER_COMPOSE_BIN="${DOCKER_COMPOSE_BIN:-docker}"
API_METRICS_URL="${API_METRICS_URL:-http://localhost:8000/metrics}"
WORKER_METRICS_URL="${WORKER_METRICS_URL:-http://localhost:9101/metrics}"

fetch_metrics() {
  local service="$1"
  local url="$2"
  "$DOCKER_COMPOSE_BIN" compose exec -T "$service" python -c "from urllib.request import urlopen; print(urlopen('$url').read().decode())"
}

api_metrics="$(fetch_metrics api "$API_METRICS_URL")"
worker_metrics="$(fetch_metrics worker "$WORKER_METRICS_URL")"

require_metric() {
  local payload="$1"
  local metric_name="$2"
  local source_name="$3"

  if ! grep -q "$metric_name" <<<"$payload"; then
    echo "Missing metric '$metric_name' from $source_name" >&2
    exit 1
  fi
}

require_metric "$api_metrics" "saasguard_api_auth_failures_total" "API metrics"
require_metric "$api_metrics" "saasguard_api_authorization_denials_total" "API metrics"
require_metric "$api_metrics" "saasguard_api_job_read_denials_total" "API metrics"
require_metric "$api_metrics" "saasguard_export_jobs" "API metrics"
require_metric "$api_metrics" "saasguard_export_job_duration_avg_seconds" "API metrics"
require_metric "$api_metrics" "saasguard_queue_backlog_jobs" "API metrics"
require_metric "$api_metrics" "saasguard_oldest_pending_job_age_seconds" "API metrics"
require_metric "$api_metrics" "saasguard_stale_processing_jobs" "API metrics"

require_metric "$worker_metrics" "saasguard_worker_jobs_started_total" "worker metrics"
require_metric "$worker_metrics" "saasguard_worker_jobs_completed_total" "worker metrics"
require_metric "$worker_metrics" "saasguard_worker_jobs_failed_total" "worker metrics"
require_metric "$worker_metrics" "saasguard_worker_job_retries_total" "worker metrics"
require_metric "$worker_metrics" "saasguard_worker_minio_upload_failures_total" "worker metrics"
require_metric "$worker_metrics" "saasguard_worker_db_query_failures_total" "worker metrics"

echo "OE metric presence verified for API and worker endpoints."
