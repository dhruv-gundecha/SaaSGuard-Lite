import json

from src.api import app
from src.auth import get_current_user
from src.operations import build_operations_summary


def _dependency(status: str, latency_ms: float | None, reason: str) -> dict:
    return {
        "status": status,
        "latency_ms": latency_ms,
        "reason": reason,
    }


def _base_operations_overview(**overrides):
    payload = {
        "queued_jobs": 2,
        "retry_pending_jobs": 1,
        "processing_jobs": 1,
        "completed_jobs_last_hour": 6,
        "failed_jobs_last_hour": 0,
        "jobs_started_last_hour": 7,
        "retry_count_last_hour": 1,
        "minio_upload_failures_last_hour": 0,
        "oldest_pending_job_age_seconds": 120,
        "active_tenant_backlog": 2,
        "authorization_denials_last_hour": 1,
        "cross_tenant_denials_last_hour": 0,
        "db_query_failures_last_hour": 0,
    }
    payload.update(overrides)
    return payload


def _base_dependencies(**overrides):
    payload = {
        "status": "healthy",
        "postgres": _dependency("healthy", 12.0, "query ok"),
        "redis": _dependency("healthy", 9.0, "ping ok"),
        "minio": _dependency("healthy", 18.0, "bucket reachable"),
        "keycloak": _dependency("healthy", 25.0, "jwks reachable"),
    }
    payload.update(overrides)
    return payload


def _base_api_activity(**overrides):
    payload = {
        "window_minutes": 5,
        "request_count": 50,
        "request_rate": 10.0,
        "error_count": 0,
        "error_rate": 0.0,
        "auth_failure_count": 2,
        "authorization_denial_count": 1,
        "p95_latency_ms": 210.0,
    }
    payload.update(overrides)
    return payload


def _base_worker_totals(**overrides):
    payload = {
        "jobs_started_total": 12.0,
        "jobs_completed_total": 10.0,
        "jobs_failed_total": 1.0,
        "retries_total": 2.0,
        "minio_upload_failures_total": 1.0,
        "db_query_failures_total": 0.0,
    }
    payload.update(overrides)
    return payload


def test_operations_summary_endpoint_returns_expected_structure(
    client, alice_user, monkeypatch
):
    expected = {
        "generated_at": "2026-05-17T10:00:00+00:00",
        "scope": {
            "tenant_id": "tenant_alpha",
            "tenant_name": "Tenant Alpha",
            "role": "analyst",
        },
        "overall_status": "healthy",
        "api": {"status": "healthy"},
        "exports": {"status": "healthy"},
        "worker": {"status": "healthy"},
        "security": {"status": "healthy"},
        "dependencies": {"status": "healthy"},
        "deployment": {"status": "healthy", "suspected_regression": False},
        "links": {"grafana": "http://localhost:3000"},
    }

    app.dependency_overrides[get_current_user] = lambda: alice_user
    monkeypatch.setattr("src.api.build_operations_summary", lambda **_: expected)

    response = client.get("/operations/summary")

    assert response.status_code == 200
    assert response.json()["overall_status"] == "healthy"
    assert response.json()["scope"]["tenant_id"] == "tenant_alpha"
    assert "dependencies" in response.json()


def test_build_operations_summary_avoids_secret_values(monkeypatch):
    monkeypatch.setattr(
        "src.operations.get_operations_overview",
        lambda tenant_id: _base_operations_overview(),
    )
    monkeypatch.setattr(
        "src.operations.collect_dependency_health",
        lambda: _base_dependencies(),
    )
    monkeypatch.setattr(
        "src.operations.summarize_recent_api_activity",
        lambda: _base_api_activity(),
    )
    monkeypatch.setattr(
        "src.operations.collect_worker_metric_totals",
        lambda: _base_worker_totals(),
    )

    summary = build_operations_summary(
        tenant_id="tenant_alpha",
        tenant_name="Tenant Alpha",
        role="analyst",
    )
    encoded = json.dumps(summary)

    assert "minioadmin" not in encoded
    assert "saasguard-dev-secret" not in encoded
    assert "Bearer " not in encoded
    assert summary["links"]["loki"] == "http://localhost:3000/explore"


def test_build_operations_summary_calculates_queue_backlog_and_failed_export_signals(
    monkeypatch,
):
    monkeypatch.setattr(
        "src.operations.get_operations_overview",
        lambda tenant_id: _base_operations_overview(
            queued_jobs=9,
            retry_pending_jobs=4,
            failed_jobs_last_hour=3,
            oldest_pending_job_age_seconds=420,
        ),
    )
    monkeypatch.setattr(
        "src.operations.collect_dependency_health",
        lambda: _base_dependencies(),
    )
    monkeypatch.setattr(
        "src.operations.summarize_recent_api_activity",
        lambda: _base_api_activity(),
    )
    monkeypatch.setattr(
        "src.operations.collect_worker_metric_totals",
        lambda: _base_worker_totals(retries_total=6.0),
    )

    summary = build_operations_summary(
        tenant_id="tenant_alpha",
        tenant_name="Tenant Alpha",
        role="analyst",
    )

    assert summary["exports"]["queued"] == 9
    assert summary["exports"]["retry_pending"] == 4
    assert summary["exports"]["status"] == "degraded"
    assert summary["exports"]["oldest_pending_age_seconds"] == 420


def test_build_operations_summary_marks_dependency_failure_as_unhealthy(monkeypatch):
    monkeypatch.setattr(
        "src.operations.get_operations_overview",
        lambda tenant_id: _base_operations_overview(),
    )
    monkeypatch.setattr(
        "src.operations.collect_dependency_health",
        lambda: _base_dependencies(
            status="unhealthy",
            redis=_dependency("unhealthy", None, "ConnectionError"),
        ),
    )
    monkeypatch.setattr(
        "src.operations.summarize_recent_api_activity",
        lambda: _base_api_activity(error_count=5, error_rate=0.1),
    )
    monkeypatch.setattr(
        "src.operations.collect_worker_metric_totals",
        lambda: _base_worker_totals(),
    )

    summary = build_operations_summary(
        tenant_id="tenant_alpha",
        tenant_name="Tenant Alpha",
        role="analyst",
    )

    assert summary["dependencies"]["redis"]["status"] == "unhealthy"
    assert summary["worker"]["status"] == "unhealthy"
    assert summary["overall_status"] == "unhealthy"


def test_build_operations_summary_detects_release_regression_signal(monkeypatch):
    monkeypatch.setattr(
        "src.operations.get_operations_overview",
        lambda tenant_id: _base_operations_overview(failed_jobs_last_hour=2),
    )
    monkeypatch.setattr(
        "src.operations.collect_dependency_health",
        lambda: _base_dependencies(),
    )
    monkeypatch.setattr(
        "src.operations.summarize_recent_api_activity",
        lambda: _base_api_activity(error_count=3, error_rate=0.04, p95_latency_ms=950.0),
    )
    monkeypatch.setattr(
        "src.operations.collect_worker_metric_totals",
        lambda: _base_worker_totals(),
    )

    summary = build_operations_summary(
        tenant_id="tenant_alpha",
        tenant_name="Tenant Alpha",
        role="analyst",
    )

    assert summary["api"]["status"] == "degraded"
    assert summary["deployment"]["suspected_regression"] is True
    assert summary["deployment"]["status"] == "degraded"
