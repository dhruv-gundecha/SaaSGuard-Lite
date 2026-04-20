from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

from src.config import get_settings


settings = get_settings()
tenant_labels = ["tenant_id"] if settings.metrics_tenant_labels_enabled else []

api_requests_total = Counter(
    "saasguard_api_requests_total",
    "Total API requests",
    ["method", "path", "status_code"],
)
api_request_latency_seconds = Histogram(
    "saasguard_api_request_latency_seconds",
    "API request latency in seconds",
    ["method", "path"],
)
api_auth_failures_total = Counter(
    "saasguard_api_auth_failures_total",
    "Authentication failures in the API",
)
api_authorization_denials_total = Counter(
    "saasguard_api_authorization_denials_total",
    "Authorization denials in the API",
    ["action"],
)
api_export_requests_created_total = Counter(
    "saasguard_api_export_requests_created_total",
    "Export requests created by the API",
    tenant_labels + ["role"],
)
api_job_read_denials_total = Counter(
    "saasguard_api_job_read_denials_total",
    "Denied job read attempts",
)

worker_jobs_started_total = Counter(
    "saasguard_worker_jobs_started_total",
    "Worker jobs started",
    tenant_labels,
)
worker_jobs_completed_total = Counter(
    "saasguard_worker_jobs_completed_total",
    "Worker jobs completed",
    tenant_labels,
)
worker_jobs_failed_total = Counter(
    "saasguard_worker_jobs_failed_total",
    "Worker jobs failed",
    tenant_labels + ["stage"],
)
worker_job_retries_total = Counter(
    "saasguard_worker_job_retries_total",
    "Worker job retries",
    tenant_labels + ["stage"],
)
worker_job_duration_seconds = Histogram(
    "saasguard_worker_job_duration_seconds",
    "Worker job duration in seconds",
    tenant_labels,
)
worker_queue_wait_seconds = Histogram(
    "saasguard_worker_queue_wait_seconds",
    "Queue wait time in seconds",
    tenant_labels,
)
worker_db_query_failures_total = Counter(
    "saasguard_worker_db_query_failures_total",
    "Worker database query failures",
    ["operation"],
)
worker_minio_upload_failures_total = Counter(
    "saasguard_worker_minio_upload_failures_total",
    "Worker MinIO upload failures",
)
worker_export_row_count = Histogram(
    "saasguard_worker_export_row_count",
    "Row count per export job",
    tenant_labels,
    buckets=(0, 1, 10, 100, 1000, 10000),
)
queue_backlog_jobs = Gauge(
    "saasguard_queue_backlog_jobs",
    "Number of queued jobs awaiting worker execution",
)
oldest_pending_job_age_seconds = Gauge(
    "saasguard_oldest_pending_job_age_seconds",
    "Age of the oldest queued job in seconds",
)


def tenant_metric_labels(tenant_id: str) -> dict[str, str]:
    if settings.metrics_tenant_labels_enabled:
        return {"tenant_id": tenant_id}
    return {}


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
