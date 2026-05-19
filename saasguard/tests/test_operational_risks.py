from datetime import UTC, datetime
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError

from src.metrics import (
    api_auth_failures_total,
    tenant_metric_labels,
    worker_jobs_failed_total,
    worker_minio_upload_failures_total,
)
from src.tasks import export_job


def _job_record(
    *,
    job_id,
    tenant_id: str,
    requester_user_id: str,
    requester_role: str = "analyst",
    status: str = "queued",
):
    now = datetime.now(UTC)
    return {
        "id": job_id,
        "tenant_id": tenant_id,
        "requester_user_id": requester_user_id,
        "requester_role": requester_role,
        "status": status,
        "object_key": None,
        "error_message": None,
        "failure_stage": None,
        "correlation_id": uuid4(),
        "retry_count": 0,
        "created_at": now,
        "updated_at": now,
        "started_at": now if status == "processing" else None,
        "completed_at": None,
    }


def test_health_endpoint_is_available_without_auth(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_missing_bearer_token_increments_auth_failure_metric(client):
    before = api_auth_failures_total._value.get()

    response = client.get("/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing bearer token"}
    assert api_auth_failures_total._value.get() >= before + 1


def test_worker_upload_failure_marks_job_failed_and_records_metrics(monkeypatch):
    queued_job_id = uuid4()
    initial_job = _job_record(
        job_id=queued_job_id,
        tenant_id="tenant_alpha",
        requester_user_id="user-alice",
        status="queued",
    )
    claimed_job = _job_record(
        job_id=queued_job_id,
        tenant_id="tenant_alpha",
        requester_user_id="user-alice",
        status="processing",
    )
    failed_jobs = []
    audit_events = []
    metric_labels = tenant_metric_labels("tenant_alpha")
    failed_before = worker_jobs_failed_total.labels(
        failure_stage="upload", **metric_labels
    )._value.get()
    minio_before = worker_minio_upload_failures_total.labels(
        failure_stage="upload", **metric_labels
    )._value.get()

    monkeypatch.setattr(
        "src.tasks.get_job", lambda job_id: initial_job if job_id == queued_job_id else None
    )
    monkeypatch.setattr(
        "src.tasks.claim_job_for_processing",
        lambda job_id: claimed_job if job_id == queued_job_id else None,
    )
    monkeypatch.setattr(
        "src.tasks.fetch_tenant_records",
        lambda tenant_id: [
            {
                "id": "row-1",
                "tenant_id": tenant_id,
                "account_name": "Acme",
                "plan_name": "Pro",
                "monthly_spend": "42.00",
                "created_at": "2026-04-26T00:00:00Z",
            }
        ],
    )
    monkeypatch.setattr(
        "src.tasks.upload_csv",
        lambda object_key, payload: (_ for _ in ()).throw(
            ClientError(
                error_response={
                    "Error": {"Code": "ServiceUnavailable", "Message": "storage down"}
                },
                operation_name="PutObject",
            )
        ),
    )
    monkeypatch.setattr(
        "src.tasks.append_job_retry",
        lambda job_id, error_message, failure_stage: {
            "id": job_id,
            "retry_count": 999,
            "correlation_id": claimed_job["correlation_id"],
            "tenant_id": claimed_job["tenant_id"],
            "requester_user_id": claimed_job["requester_user_id"],
        },
    )
    monkeypatch.setattr(
        "src.tasks.mark_job_failed",
        lambda job_id, error_message, failure_stage: failed_jobs.append(
            (job_id, error_message, failure_stage)
        ),
    )
    monkeypatch.setattr("src.tasks.record_audit_event", lambda **kwargs: audit_events.append(kwargs))

    export_job.run(str(queued_job_id))

    assert failed_jobs == [
        (queued_job_id, "failed to upload export object", "upload")
    ]
    assert (
        worker_minio_upload_failures_total.labels(
            failure_stage="upload", **metric_labels
        )._value.get()
        >= minio_before + 1
    )
    assert (
        worker_jobs_failed_total.labels(
            failure_stage="upload", **metric_labels
        )._value.get()
        >= failed_before + 1
    )
    assert audit_events
    assert audit_events[0]["action"] == "export.failed"
    assert audit_events[0]["outcome"] == "failed"
    assert audit_events[0]["reason"] == "failed to upload export object"


def test_metrics_endpoint_emits_oe_dashboard_metrics(client, monkeypatch):
    monkeypatch.setattr(
        "src.api.get_worker_stats",
        lambda: {"queued_jobs": 4, "oldest_pending_job_age_seconds": 180},
    )
    monkeypatch.setattr(
        "src.api.get_export_job_metrics_snapshot",
        lambda: {
            "status_counts": [
                {"tenant_id": "tenant_alpha", "status": "failed", "job_count": 2},
                {"tenant_id": "tenant_alpha", "status": "retry_pending", "job_count": 1},
            ],
            "failure_stage_counts": [
                {
                    "tenant_id": "tenant_alpha",
                    "status": "failed",
                    "failure_stage": "upload",
                    "job_count": 2,
                }
            ],
            "duration_averages": [
                {"tenant_id": "tenant_alpha", "avg_duration_seconds": 32.5}
            ],
            "stale_processing": [
                {"tenant_id": "tenant_alpha", "stale_processing_jobs": 1}
            ],
        },
    )

    response = client.get("/metrics")

    assert response.status_code == 200
    payload = response.text
    assert "saasguard_export_jobs" in payload
    assert "saasguard_export_jobs_by_failure_stage" in payload
    assert "saasguard_export_job_duration_avg_seconds" in payload
    assert "saasguard_stale_processing_jobs" in payload
    assert 'status="failed"' in payload
    assert 'failure_stage="upload"' in payload
