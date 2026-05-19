import math
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any
from urllib import error, request

import boto3
import psycopg
import redis
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from src.config import get_settings
from src.db import get_operations_overview


API_WINDOW_SECONDS = 300
_api_request_events: deque[tuple[float, int, float]] = deque()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _trim_api_events(now: float) -> None:
    cutoff = now - API_WINDOW_SECONDS
    while _api_request_events and _api_request_events[0][0] < cutoff:
        _api_request_events.popleft()


def record_api_request_observation(status_code: int, latency_seconds: float) -> None:
    now = time.time()
    _api_request_events.append((now, status_code, latency_seconds))
    _trim_api_events(now)


def summarize_recent_api_activity() -> dict[str, float | int]:
    now = time.time()
    _trim_api_events(now)
    request_count = len(_api_request_events)
    if request_count == 0:
        return {
            "window_minutes": API_WINDOW_SECONDS / 60,
            "request_count": 0,
            "request_rate": 0.0,
            "error_count": 0,
            "error_rate": 0.0,
            "auth_failure_count": 0,
            "authorization_denial_count": 0,
            "p95_latency_ms": 0.0,
        }

    error_count = sum(1 for _, status_code, _ in _api_request_events if status_code >= 500)
    auth_failure_count = sum(1 for _, status_code, _ in _api_request_events if status_code == 401)
    authorization_denial_count = sum(
        1 for _, status_code, _ in _api_request_events if status_code == 403
    )
    latencies_ms = sorted(latency_seconds * 1000 for _, _, latency_seconds in _api_request_events)
    percentile_index = max(math.ceil(0.95 * request_count) - 1, 0)

    return {
        "window_minutes": API_WINDOW_SECONDS / 60,
        "request_count": request_count,
        "request_rate": round(request_count / (API_WINDOW_SECONDS / 60), 2),
        "error_count": error_count,
        "error_rate": round(error_count / request_count, 4),
        "auth_failure_count": auth_failure_count,
        "authorization_denial_count": authorization_denial_count,
        "p95_latency_ms": round(latencies_ms[percentile_index], 2),
    }


def _health_status_from_latency(latency_ms: float | None, *, degraded_ms: float = 250, unhealthy_ms: float = 1000) -> str:
    if latency_ms is None:
        return "healthy"
    if latency_ms >= unhealthy_ms:
        return "unhealthy"
    if latency_ms >= degraded_ms:
        return "degraded"
    return "healthy"


def _bounded_postgres_health() -> dict[str, Any]:
    settings = get_settings()
    started_at = time.perf_counter()
    try:
        with psycopg.connect(settings.postgres_dsn, connect_timeout=1) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        return {
            "status": _health_status_from_latency(latency_ms, degraded_ms=200, unhealthy_ms=750),
            "latency_ms": latency_ms,
            "reason": "query ok",
        }
    except Exception as exc:
        return {
            "status": "unhealthy",
            "latency_ms": None,
            "reason": type(exc).__name__,
        }


def _bounded_redis_health() -> dict[str, Any]:
    settings = get_settings()
    started_at = time.perf_counter()
    try:
        client = redis.Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        client.ping()
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        return {
            "status": _health_status_from_latency(latency_ms, degraded_ms=100, unhealthy_ms=500),
            "latency_ms": latency_ms,
            "reason": "ping ok",
        }
    except Exception as exc:
        return {
            "status": "unhealthy",
            "latency_ms": None,
            "reason": type(exc).__name__,
        }


def _bounded_minio_health() -> dict[str, Any]:
    settings = get_settings()
    started_at = time.perf_counter()
    try:
        client = boto3.client(
            "s3",
            endpoint_url=f"http{'s' if settings.minio_secure else ''}://{settings.minio_endpoint}",
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            config=Config(signature_version="s3v4", connect_timeout=1, read_timeout=2),
            region_name="us-east-1",
        )
        client.head_bucket(Bucket=settings.minio_bucket)
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        return {
            "status": _health_status_from_latency(latency_ms, degraded_ms=250, unhealthy_ms=1000),
            "latency_ms": latency_ms,
            "reason": "bucket reachable",
        }
    except (BotoCoreError, ClientError, Exception) as exc:
        return {
            "status": "unhealthy",
            "latency_ms": None,
            "reason": type(exc).__name__,
        }


def _bounded_keycloak_health() -> dict[str, Any]:
    settings = get_settings()
    started_at = time.perf_counter()
    try:
        with request.urlopen(settings.oidc_jwks_url, timeout=2) as response:
            if response.status >= 500:
                raise RuntimeError(f"http_{response.status}")
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        return {
            "status": _health_status_from_latency(latency_ms, degraded_ms=400, unhealthy_ms=1500),
            "latency_ms": latency_ms,
            "reason": "jwks reachable",
        }
    except (error.URLError, RuntimeError, Exception) as exc:
        return {
            "status": "unhealthy",
            "latency_ms": None,
            "reason": type(exc).__name__,
        }


def collect_dependency_health() -> dict[str, Any]:
    checks = {
        "postgres": _bounded_postgres_health(),
        "redis": _bounded_redis_health(),
        "minio": _bounded_minio_health(),
        "keycloak": _bounded_keycloak_health(),
    }
    statuses = [check["status"] for check in checks.values()]
    if "unhealthy" in statuses:
        overall_status = "unhealthy"
    elif "degraded" in statuses:
        overall_status = "degraded"
    else:
        overall_status = "healthy"
    return {"status": overall_status, **checks}


def _parse_prometheus_counter_totals(payload: str, metric_name: str) -> float:
    total = 0.0
    prefix = f"{metric_name}"
    for line in payload.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or not stripped.startswith(prefix):
            continue
        value = stripped.split(" ", 1)[1]
        total += float(value)
    return total


def collect_worker_metric_totals() -> dict[str, float]:
    worker_metrics_url = f"http://worker:{get_settings().worker_metrics_port}/metrics"
    try:
        with request.urlopen(worker_metrics_url, timeout=2) as response:
            payload = response.read().decode("utf-8")
    except Exception:
        return {
            "jobs_started_total": 0.0,
            "jobs_completed_total": 0.0,
            "jobs_failed_total": 0.0,
            "retries_total": 0.0,
            "minio_upload_failures_total": 0.0,
            "db_query_failures_total": 0.0,
        }

    return {
        "jobs_started_total": _parse_prometheus_counter_totals(
            payload, "saasguard_worker_jobs_started_total"
        ),
        "jobs_completed_total": _parse_prometheus_counter_totals(
            payload, "saasguard_worker_jobs_completed_total"
        ),
        "jobs_failed_total": _parse_prometheus_counter_totals(
            payload, "saasguard_worker_jobs_failed_total"
        ),
        "retries_total": _parse_prometheus_counter_totals(
            payload, "saasguard_worker_job_retries_total"
        ),
        "minio_upload_failures_total": _parse_prometheus_counter_totals(
            payload, "saasguard_worker_minio_upload_failures_total"
        ),
        "db_query_failures_total": _parse_prometheus_counter_totals(
            payload, "saasguard_worker_db_query_failures_total"
        ),
    }


def _status_rank(status: str) -> int:
    return {"healthy": 0, "degraded": 1, "unhealthy": 2}.get(status, 1)


def _max_status(*statuses: str) -> str:
    ranked = max(statuses, key=_status_rank)
    return ranked


def _api_status(summary: dict[str, Any], dependencies: dict[str, Any]) -> str:
    if dependencies["postgres"]["status"] == "unhealthy" or dependencies["keycloak"]["status"] == "unhealthy":
        return "unhealthy"
    if summary["error_rate"] >= 0.1 or summary["p95_latency_ms"] >= 2000:
        return "unhealthy"
    if summary["error_rate"] >= 0.02 or summary["p95_latency_ms"] >= 800:
        return "degraded"
    return "healthy"


def _export_status(summary: dict[str, Any]) -> str:
    backlog = summary["queued_jobs"] + summary["retry_pending_jobs"]
    if summary["oldest_pending_job_age_seconds"] >= 900 or summary["failed_jobs_last_hour"] >= 5:
        return "unhealthy"
    if backlog >= 10 or summary["oldest_pending_job_age_seconds"] >= 300 or summary["failed_jobs_last_hour"] > 0:
        return "degraded"
    return "healthy"


def _worker_status(summary: dict[str, Any], dependencies: dict[str, Any]) -> str:
    if (
        dependencies["redis"]["status"] == "unhealthy"
        or dependencies["postgres"]["status"] == "unhealthy"
        or dependencies["minio"]["status"] == "unhealthy"
    ):
        return "unhealthy"
    if summary["retry_count_last_hour"] >= 10 or summary["db_query_failures_last_hour"] >= 3:
        return "unhealthy"
    if (
        summary["failed_jobs_last_hour"] > 0
        or summary["retry_count_last_hour"] > 0
        or summary["minio_upload_failures_last_hour"] > 0
    ):
        return "degraded"
    return "healthy"


def _security_status(summary: dict[str, Any], api_activity: dict[str, Any]) -> str:
    if summary["cross_tenant_denials_last_hour"] >= 5:
        return "unhealthy"
    if (
        summary["cross_tenant_denials_last_hour"] > 0
        or summary["authorization_denials_last_hour"] >= 10
        or api_activity["error_count"] > 0 and api_activity["request_count"] > 0 and api_activity["error_rate"] >= 0.1
    ):
        return "degraded"
    if api_activity["request_count"] > 0 and api_activity["request_rate"] > 0 and api_activity["error_rate"] == 0:
        return "healthy"
    return "healthy"


def _deployment_status(api_status: str, worker_status: str, dependencies: dict[str, Any]) -> tuple[str, bool]:
    healthy_dependencies = all(
        dependencies[name]["status"] == "healthy"
        for name in ("postgres", "redis", "minio", "keycloak")
    )
    suspected_regression = healthy_dependencies and (
        api_status in {"degraded", "unhealthy"} or worker_status in {"degraded", "unhealthy"}
    )
    if suspected_regression and (api_status == "unhealthy" or worker_status == "unhealthy"):
        return "unhealthy", True
    if suspected_regression:
        return "degraded", True
    return "healthy", False


def _impact_copy(status: str, *, healthy: str, degraded: str, unhealthy: str) -> str:
    if status == "unhealthy":
        return unhealthy
    if status == "degraded":
        return degraded
    return healthy


def build_operations_summary(*, role: str) -> dict[str, Any]:
    operations = get_operations_overview()
    dependencies = collect_dependency_health()
    api_activity = summarize_recent_api_activity()
    worker_totals = collect_worker_metric_totals()

    api_status = _api_status(api_activity, dependencies)
    exports_status = _export_status(operations)
    worker_status = _worker_status(operations, dependencies)
    security_status = _security_status(operations, api_activity)
    deployment_status, suspected_regression = _deployment_status(
        api_status, worker_status, dependencies
    )
    overall_status = _max_status(
        api_status,
        exports_status,
        worker_status,
        security_status,
        dependencies["status"],
        deployment_status,
    )

    return {
        "generated_at": _utc_now().isoformat(),
        "scope": {
            "type": "global",
            "role": role,
        },
        "overall_status": overall_status,
        "api": {
            "status": api_status,
            **api_activity,
            "impact": _impact_copy(
                api_status,
                healthy="API traffic and latency look stable enough for customers to log in and request exports.",
                degraded="Users may notice slower responses or intermittent errors before a full outage.",
                unhealthy="The API is likely disrupting logins, job creation, or download access right now.",
            ),
        },
        "exports": {
            "status": exports_status,
            "queued": operations["queued_jobs"],
            "retry_pending": operations["retry_pending_jobs"],
            "processing": operations["processing_jobs"],
            "completed_last_hour": operations["completed_jobs_last_hour"],
            "failed_last_hour": operations["failed_jobs_last_hour"],
            "oldest_pending_age_seconds": operations["oldest_pending_job_age_seconds"],
            "impact": _impact_copy(
                exports_status,
                healthy="The export pipeline is moving work through to completion without visible backlog pressure.",
                degraded="Customers may experience slower report delivery or a growing queue.",
                unhealthy="Exports are likely stuck or failing often enough to disrupt report delivery.",
            ),
        },
        "worker": {
            "status": worker_status,
            "jobs_started": int(worker_totals["jobs_started_total"]),
            "jobs_completed": int(worker_totals["jobs_completed_total"]),
            "jobs_failed": int(worker_totals["jobs_failed_total"]),
            "retry_count": int(worker_totals["retries_total"]),
            "minio_upload_failures": int(worker_totals["minio_upload_failures_total"]),
            "db_query_failures": int(worker_totals["db_query_failures_total"]),
            "jobs_started_last_hour": operations["jobs_started_last_hour"],
            "jobs_failed_last_hour": operations["failed_jobs_last_hour"],
            "retries_last_hour": operations["retry_count_last_hour"],
            "impact": _impact_copy(
                worker_status,
                healthy="The worker is turning queued jobs into completed exports at a normal pace.",
                degraded="Retries or dependency trouble may delay export completion and increase queue age.",
                unhealthy="Worker instability is likely preventing exports from completing reliably.",
            ),
        },
        "security": {
            "status": security_status,
            "auth_failures": api_activity["auth_failure_count"],
            "authorization_denials": operations["authorization_denials_last_hour"],
            "cross_tenant_denials": operations["cross_tenant_denials_last_hour"],
            "impact": _impact_copy(
                security_status,
                healthy="Authorization signals are quiet and there is no recent evidence of cross-tenant probing.",
                degraded="Rising denials suggest user confusion, probing, or a policy misconfiguration worth checking now.",
                unhealthy="Cross-tenant denial activity is high enough to demand immediate review of authz behavior and logs.",
            ),
        },
        "dependencies": dependencies,
        "deployment": {
            "status": deployment_status,
            "suspected_regression": suspected_regression,
            "impact": _impact_copy(
                deployment_status,
                healthy="Current instability does not strongly suggest a fresh release regression.",
                degraded="Application-level degradation with healthy dependencies may point to a recent release issue.",
                unhealthy="Healthy dependencies plus broken app behavior strongly suggest a release or config regression.",
            ),
        },
        "links": {
            "grafana": "http://localhost:3000",
            "grafana_service_health": "http://localhost:3000/d/saasguard-service-health",
            "grafana_tenant_impact": "http://localhost:3000/d/saasguard-tenant-impact",
            "grafana_auth_security": "http://localhost:3000/d/saasguard-auth-security",
            "prometheus": "http://localhost:9090",
            "loki": "http://localhost:3000/explore",
            "uptime_kuma": "http://localhost:3002",
            "minio_console": "http://localhost:9001",
        },
    }
