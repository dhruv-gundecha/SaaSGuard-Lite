from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from src.api import app
from src.auth import get_current_user
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


def test_get_job_denies_cross_tenant_access(client, bob_user, monkeypatch):
    alpha_job_id = uuid4()
    alpha_job = _job_record(
        job_id=alpha_job_id,
        tenant_id="tenant_alpha",
        requester_user_id="user-alice",
    )

    app.dependency_overrides[get_current_user] = lambda: bob_user
    monkeypatch.setattr("src.api.record_audit_event", lambda **_: None)
    monkeypatch.setattr("src.api.get_job_for_tenant", lambda job_id, tenant_id: None)
    monkeypatch.setattr(
        "src.api.get_job", lambda job_id: alpha_job if job_id == alpha_job_id else None
    )

    response = client.get(f"/jobs/{alpha_job_id}")

    assert response.status_code == 403
    assert response.json() == {"detail": "Access to this job is denied"}
    assert "tenant_id" not in response.text
    assert "requester_user_id" not in response.text


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
