from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from src.api import app
from src.auth import get_current_user
from src.metrics import api_tenant_authorization_denials_total, tenant_metric_labels
from src.tasks import export_job


def _job_record(
    *,
    job_id,
    tenant_id: str,
    requester_user_id: str,
    requester_role: str = "analyst",
    status: str = "queued",
    object_key: str | None = None,
):
    now = datetime.now(UTC)
    return {
        "id": job_id,
        "tenant_id": tenant_id,
        "requester_user_id": requester_user_id,
        "requester_role": requester_role,
        "status": status,
        "object_key": object_key,
        "error_message": None,
        "failure_stage": None,
        "correlation_id": uuid4(),
        "retry_count": 0,
        "created_at": now,
        "updated_at": now,
        "started_at": now if status == "processing" else None,
        "completed_at": now if status == "completed" else None,
    }


def test_post_exports_creates_job_for_authorized_analyst_and_enqueues_only_job_id(
    client, alice_user, monkeypatch
):
    created_job = _job_record(
        job_id=uuid4(),
        tenant_id="tenant_alpha",
        requester_user_id=alice_user.user_id,
    )
    create_job_calls = []
    delay_calls = []

    app.dependency_overrides[get_current_user] = lambda: alice_user
    monkeypatch.setattr("src.api.record_audit_event", lambda **_: None)

    def fake_create_job(**kwargs):
        create_job_calls.append(kwargs)
        return created_job

    def fake_delay(*args, **kwargs):
        delay_calls.append((args, kwargs))

    monkeypatch.setattr("src.api.create_job", fake_create_job)
    monkeypatch.setattr("src.api.export_job", SimpleNamespace(delay=fake_delay))

    response = client.post("/exports")

    assert response.status_code == 202
    assert response.json()["job_id"] == str(created_job["id"])
    assert response.json()["tenant_id"] == "tenant_alpha"
    assert len(create_job_calls) == 1
    assert create_job_calls[0]["tenant_id"] == "tenant_alpha"
    assert create_job_calls[0]["requester_user_id"] == alice_user.user_id
    assert create_job_calls[0]["requester_role"] == "analyst"
    assert isinstance(create_job_calls[0]["correlation_id"], str)
    assert delay_calls == [((str(created_job["id"]),), {})]


def test_post_exports_rate_limits_excessive_requests(client, alice_user, monkeypatch):
    created_job = _job_record(
        job_id=uuid4(),
        tenant_id="tenant_alpha",
        requester_user_id=alice_user.user_id,
    )
    create_job_calls = []
    audit_events = []

    app.dependency_overrides[get_current_user] = lambda: alice_user
    monkeypatch.setattr("src.api.create_job", lambda **kwargs: create_job_calls.append(kwargs) or created_job)
    monkeypatch.setattr("src.api.export_job", SimpleNamespace(delay=lambda *args, **kwargs: None))
    monkeypatch.setattr("src.api.record_audit_event", lambda **kwargs: audit_events.append(kwargs))
    monkeypatch.setattr(
        "src.rate_limit.get_settings",
        lambda: SimpleNamespace(
            export_request_rate_limit_count=2,
            export_request_rate_limit_window_seconds=60,
        ),
    )

    first = client.post("/exports")
    second = client.post("/exports")
    third = client.post("/exports")

    assert first.status_code == 202
    assert second.status_code == 202
    assert third.status_code == 429
    assert third.json() == {"detail": "Export request rate limit exceeded"}
    assert len(create_job_calls) == 2
    assert audit_events[-1]["action"] == "export.rate_limited"
    assert audit_events[-1]["outcome"] == "denied"


def test_get_job_denies_cross_tenant_access(client, bob_user, monkeypatch):
    alpha_job_id = uuid4()
    alpha_job = _job_record(
        job_id=alpha_job_id,
        tenant_id="tenant_alpha",
        requester_user_id="user-alice",
    )
    audit_events = []
    before = api_tenant_authorization_denials_total.labels(
        action="job.viewed", **tenant_metric_labels("tenant_beta")
    )._value.get()

    app.dependency_overrides[get_current_user] = lambda: bob_user
    monkeypatch.setattr("src.authz.record_audit_event", lambda **kwargs: audit_events.append(kwargs))
    monkeypatch.setattr("src.api.get_job_for_tenant", lambda job_id, tenant_id: None)
    monkeypatch.setattr(
        "src.api.get_job", lambda job_id: alpha_job if job_id == alpha_job_id else None
    )

    response = client.get(f"/jobs/{alpha_job_id}")

    assert response.status_code == 403
    assert response.json() == {"detail": "Access to this job is denied"}
    assert "tenant_id" not in response.text
    assert "requester_user_id" not in response.text
    assert audit_events
    assert audit_events[0]["action"] == "authorization.denied"
    assert audit_events[0]["outcome"] == "denied"
    assert audit_events[0]["reason"] == "job.viewed: cross-tenant access denied"
    after = api_tenant_authorization_denials_total.labels(
        action="job.viewed", **tenant_metric_labels("tenant_beta")
    )._value.get()
    assert after == before + 1


def test_worker_reloads_authoritative_job_context_from_database(monkeypatch):
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
    fetch_calls = []
    uploaded = {}
    completed = []

    monkeypatch.setattr(
        "src.tasks.get_job", lambda job_id: initial_job if job_id == queued_job_id else None
    )
    monkeypatch.setattr(
        "src.tasks.claim_job_for_processing",
        lambda job_id: claimed_job if job_id == queued_job_id else None,
    )
    monkeypatch.setattr(
        "src.tasks.fetch_tenant_records",
        lambda tenant_id: fetch_calls.append(tenant_id)
        or [
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
        lambda object_key, payload: uploaded.update(
            {"object_key": object_key, "payload": payload.decode("utf-8")}
        ),
    )
    monkeypatch.setattr(
        "src.tasks.mark_job_completed",
        lambda job_id, object_key: completed.append((job_id, object_key)),
    )
    monkeypatch.setattr("src.tasks.record_audit_event", lambda **_: None)

    export_job.run(str(queued_job_id))

    assert fetch_calls == ["tenant_alpha"]
    assert uploaded["object_key"] == f"exports/tenant_alpha/{queued_job_id}.csv"
    assert "tenant_beta" not in uploaded["payload"]
    assert completed == [(queued_job_id, f"exports/tenant_alpha/{queued_job_id}.csv")]


def test_completed_job_can_be_downloaded_by_same_tenant_authorized_user(
    client, alice_user, monkeypatch
):
    job_id = uuid4()
    job = _job_record(
        job_id=job_id,
        tenant_id="tenant_alpha",
        requester_user_id=alice_user.user_id,
        status="completed",
        object_key=f"exports/tenant_alpha/{job_id}.csv",
    )
    audit_events = []

    app.dependency_overrides[get_current_user] = lambda: alice_user
    monkeypatch.setattr("src.api.get_job", lambda requested_job_id: job if requested_job_id == job_id else None)
    monkeypatch.setattr("src.api.download_csv", lambda object_key: b"id,tenant_id\n1,tenant_alpha\n")
    monkeypatch.setattr("src.api.record_audit_event", lambda **kwargs: audit_events.append(kwargs))

    response = client.get(f"/jobs/{job_id}/download")

    assert response.status_code == 200
    assert response.text == "id,tenant_id\n1,tenant_alpha\n"
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"] == f'attachment; filename="{job_id}.csv"'
    assert audit_events
    assert audit_events[0]["action"] == "export.downloaded"
    assert audit_events[0]["tenant_id"] == "tenant_alpha"
    assert audit_events[0]["actor_user_id"] == alice_user.user_id
    assert audit_events[0]["target_id"] == str(job_id)
    assert audit_events[0]["outcome"] == "success"


def test_cross_tenant_download_is_denied(client, bob_user, monkeypatch):
    job_id = uuid4()
    job = _job_record(
        job_id=job_id,
        tenant_id="tenant_alpha",
        requester_user_id="user-alice",
        status="completed",
        object_key=f"exports/tenant_alpha/{job_id}.csv",
    )
    audit_events = []

    app.dependency_overrides[get_current_user] = lambda: bob_user
    monkeypatch.setattr("src.api.get_job", lambda requested_job_id: job if requested_job_id == job_id else None)
    monkeypatch.setattr("src.authz.record_audit_event", lambda **kwargs: audit_events.append(kwargs))

    response = client.get(f"/jobs/{job_id}/download")

    assert response.status_code == 403
    assert response.json() == {"detail": "Access to this export is denied"}
    assert audit_events
    assert audit_events[0]["action"] == "authorization.denied"
    assert audit_events[0]["tenant_id"] == "tenant_alpha"
    assert audit_events[0]["actor_user_id"] == bob_user.user_id
    assert audit_events[0]["target_id"] == str(job_id)
    assert audit_events[0]["outcome"] == "denied"
    assert audit_events[0]["reason"] == "export.downloaded: cross-tenant download denied"


def test_invalid_active_tenant_selection_records_authorization_denied(
    client, carol_user, monkeypatch
):
    audit_events = []

    app.dependency_overrides[get_current_user] = lambda: carol_user
    monkeypatch.setattr("src.authz.record_audit_event", lambda **kwargs: audit_events.append(kwargs))

    response = client.post("/exports", headers={"X-Active-Tenant": "tenant_gamma"})

    assert response.status_code == 403
    assert response.json() == {"detail": "Requested tenant is not available for this user"}
    assert audit_events
    assert audit_events[0]["action"] == "authorization.denied"
    assert audit_events[0]["target_id"] == "tenant_gamma"
    assert audit_events[0]["reason"] == "tenant.select: requested tenant is not available for this user"


def test_queued_job_cannot_be_downloaded(client, alice_user, monkeypatch):
    job_id = uuid4()
    job = _job_record(
        job_id=job_id,
        tenant_id="tenant_alpha",
        requester_user_id=alice_user.user_id,
        status="queued",
    )

    app.dependency_overrides[get_current_user] = lambda: alice_user
    monkeypatch.setattr("src.api.get_job", lambda requested_job_id: job if requested_job_id == job_id else None)

    response = client.get(f"/jobs/{job_id}/download")

    assert response.status_code == 409
    assert response.json() == {"detail": "Export is not ready for download"}


def test_failed_job_cannot_be_downloaded(client, alice_user, monkeypatch):
    job_id = uuid4()
    job = _job_record(
        job_id=job_id,
        tenant_id="tenant_alpha",
        requester_user_id=alice_user.user_id,
        status="failed",
    )

    app.dependency_overrides[get_current_user] = lambda: alice_user
    monkeypatch.setattr("src.api.get_job", lambda requested_job_id: job if requested_job_id == job_id else None)

    response = client.get(f"/jobs/{job_id}/download")

    assert response.status_code == 409
    assert response.json() == {"detail": "Export is not ready for download"}


def test_completed_job_without_object_key_cannot_be_downloaded(
    client, alice_user, monkeypatch
):
    job_id = uuid4()
    job = _job_record(
        job_id=job_id,
        tenant_id="tenant_alpha",
        requester_user_id=alice_user.user_id,
        status="completed",
        object_key=None,
    )

    app.dependency_overrides[get_current_user] = lambda: alice_user
    monkeypatch.setattr("src.api.get_job", lambda requested_job_id: job if requested_job_id == job_id else None)

    response = client.get(f"/jobs/{job_id}/download")

    assert response.status_code == 409
    assert response.json() == {"detail": "Completed export is unavailable for download"}


def test_missing_job_download_returns_404(client, alice_user, monkeypatch):
    missing_job_id = uuid4()

    app.dependency_overrides[get_current_user] = lambda: alice_user
    monkeypatch.setattr("src.api.get_job", lambda requested_job_id: None)

    response = client.get(f"/jobs/{missing_job_id}/download")

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}
