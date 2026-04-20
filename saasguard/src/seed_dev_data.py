from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from src.config import get_settings
from src.db import get_db_connection
from src.migrations import bootstrap_database, get_required_table_names, verify_required_tables_exist


logger = logging.getLogger("saasguard.seed")
DEMO_TENANTS = (
    {"id": "tenant_alpha", "name": "Tenant Alpha", "status": "active"},
    {"id": "tenant_beta", "name": "Tenant Beta", "status": "active"},
)

DEMO_USERS = (
    {
        "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "keycloak_sub": "11111111-1111-1111-1111-111111111111",
        "username": "alice",
        "email": "alice@tenant-alpha.local",
        "status": "active",
    },
    {
        "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "keycloak_sub": "22222222-2222-2222-2222-222222222222",
        "username": "bob",
        "email": "bob@tenant-beta.local",
        "status": "active",
    },
    {
        "id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "keycloak_sub": "33333333-3333-3333-3333-333333333333",
        "username": "carol",
        "email": "carol@saasguard.local",
        "status": "active",
    },
)

DEMO_MEMBERSHIPS = (
    {
        "id": "aaaaaaaa-0000-0000-0000-000000000001",
        "user_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "tenant_id": "tenant_alpha",
        "role": "analyst",
        "status": "active",
    },
    {
        "id": "bbbbbbbb-0000-0000-0000-000000000001",
        "user_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "tenant_id": "tenant_beta",
        "role": "analyst",
        "status": "active",
    },
    {
        "id": "cccccccc-0000-0000-0000-000000000001",
        "user_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "tenant_id": "tenant_alpha",
        "role": "tenant_admin",
        "status": "active",
    },
    {
        "id": "cccccccc-0000-0000-0000-000000000002",
        "user_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "tenant_id": "tenant_beta",
        "role": "tenant_admin",
        "status": "active",
    },
)

DEMO_TENANT_RECORDS = (
    {
        "tenant_id": "tenant_alpha",
        "account_name": "Acme Corp",
        "plan_name": "starter",
        "monthly_spend": "120.00",
        "created_at": "2026-04-01T09:00:00+00:00",
    },
    {
        "tenant_id": "tenant_alpha",
        "account_name": "Acme Sandbox",
        "plan_name": "growth",
        "monthly_spend": "480.00",
        "created_at": "2026-04-03T15:30:00+00:00",
    },
    {
        "tenant_id": "tenant_alpha",
        "account_name": "Northwind Pilot",
        "plan_name": "enterprise",
        "monthly_spend": "1540.00",
        "created_at": "2026-04-05T12:15:00+00:00",
    },
    {
        "tenant_id": "tenant_beta",
        "account_name": "Globex",
        "plan_name": "starter",
        "monthly_spend": "95.00",
        "created_at": "2026-04-02T10:45:00+00:00",
    },
    {
        "tenant_id": "tenant_beta",
        "account_name": "Globex EU",
        "plan_name": "enterprise",
        "monthly_spend": "1250.00",
        "created_at": "2026-04-04T11:20:00+00:00",
    },
    {
        "tenant_id": "tenant_beta",
        "account_name": "Initech Compliance",
        "plan_name": "growth",
        "monthly_spend": "640.00",
        "created_at": "2026-04-06T08:10:00+00:00",
    },
)


def _utc(value: str) -> datetime:
    return datetime.fromisoformat(value)


def has_required_seed_tables() -> bool:
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) AS table_count
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = ANY(%s)
            """,
            (list(get_required_table_names()),),
        )
        result = cur.fetchone() or {}
        return result.get("table_count", 0) == len(get_required_table_names())


def _job_seed_rows(now: datetime) -> tuple[dict[str, object], ...]:
    return (
        {
            "id": "10000000-0000-0000-0000-000000000001",
            "tenant_id": "tenant_alpha",
            "requester_user_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "requester_role": "analyst",
            "status": "completed",
            "object_key": "exports/tenant_alpha/2026/04/alpha-cost-rollup-20260418T091500Z.csv",
            "error_message": None,
            "failure_stage": None,
            "correlation_id": "90000000-0000-0000-0000-000000000001",
            "retry_count": 0,
            "created_at": now - timedelta(hours=30),
            "updated_at": now - timedelta(hours=29, minutes=54),
            "started_at": now - timedelta(hours=29, minutes=58),
            "completed_at": now - timedelta(hours=29, minutes=54),
        },
        {
            "id": "10000000-0000-0000-0000-000000000002",
            "tenant_id": "tenant_alpha",
            "requester_user_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "requester_role": "tenant_admin",
            "status": "completed",
            "object_key": "exports/tenant_alpha/2026/04/alpha-entitlements-20260418T153000Z.csv",
            "error_message": None,
            "failure_stage": None,
            "correlation_id": "90000000-0000-0000-0000-000000000002",
            "retry_count": 0,
            "created_at": now - timedelta(hours=18),
            "updated_at": now - timedelta(hours=17, minutes=55),
            "started_at": now - timedelta(hours=17, minutes=59),
            "completed_at": now - timedelta(hours=17, minutes=55),
        },
        {
            "id": "20000000-0000-0000-0000-000000000001",
            "tenant_id": "tenant_beta",
            "requester_user_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "requester_role": "analyst",
            "status": "completed",
            "object_key": "exports/tenant_beta/2026/04/beta-billing-20260418T101000Z.csv",
            "error_message": None,
            "failure_stage": None,
            "correlation_id": "90000000-0000-0000-0000-000000000003",
            "retry_count": 0,
            "created_at": now - timedelta(hours=26),
            "updated_at": now - timedelta(hours=25, minutes=52),
            "started_at": now - timedelta(hours=25, minutes=57),
            "completed_at": now - timedelta(hours=25, minutes=52),
        },
        {
            "id": "20000000-0000-0000-0000-000000000002",
            "tenant_id": "tenant_beta",
            "requester_user_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "requester_role": "tenant_admin",
            "status": "completed",
            "object_key": "exports/tenant_beta/2026/04/beta-usage-20260419T041200Z.csv",
            "error_message": None,
            "failure_stage": None,
            "correlation_id": "90000000-0000-0000-0000-000000000004",
            "retry_count": 0,
            "created_at": now - timedelta(hours=7),
            "updated_at": now - timedelta(hours=6, minutes=56),
            "started_at": now - timedelta(hours=6, minutes=59),
            "completed_at": now - timedelta(hours=6, minutes=56),
        },
        {
            "id": "20000000-0000-0000-0000-000000000003",
            "tenant_id": "tenant_beta",
            "requester_user_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "requester_role": "analyst",
            "status": "failed",
            "object_key": None,
            "error_message": "MinIO upload failed after 2 retries: PutObject to bucket exports returned HTTP 503 Service Unavailable",
            "failure_stage": "upload",
            "correlation_id": "90000000-0000-0000-0000-000000000005",
            "retry_count": 2,
            "created_at": now - timedelta(hours=5),
            "updated_at": now - timedelta(hours=4, minutes=43),
            "started_at": now - timedelta(hours=4, minutes=55),
            "completed_at": now - timedelta(hours=4, minutes=43),
        },
        {
            "id": "10000000-0000-0000-0000-000000000003",
            "tenant_id": "tenant_alpha",
            "requester_user_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "requester_role": "analyst",
            "status": "queued",
            "object_key": None,
            "error_message": None,
            "failure_stage": None,
            "correlation_id": "90000000-0000-0000-0000-000000000006",
            "retry_count": 0,
            "created_at": now - timedelta(minutes=42),
            "updated_at": now - timedelta(minutes=42),
            "started_at": None,
            "completed_at": None,
        },
        {
            "id": "20000000-0000-0000-0000-000000000004",
            "tenant_id": "tenant_beta",
            "requester_user_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "requester_role": "tenant_admin",
            "status": "processing",
            "object_key": None,
            "error_message": None,
            "failure_stage": None,
            "correlation_id": "90000000-0000-0000-0000-000000000007",
            "retry_count": 0,
            "created_at": now - timedelta(minutes=18),
            "updated_at": now - timedelta(minutes=6),
            "started_at": now - timedelta(minutes=16),
            "completed_at": None,
        },
    )


def _audit_seed_rows(now: datetime) -> tuple[dict[str, object], ...]:
    return (
        {
            "id": "70000000-0000-0000-0000-000000000001",
            "event_time": now - timedelta(hours=18),
            "actor_user_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "actor_sub": "33333333-3333-3333-3333-333333333333",
            "tenant_id": "tenant_alpha",
            "action": "export.requested",
            "target_type": "export_job",
            "target_id": "10000000-0000-0000-0000-000000000002",
            "outcome": "success",
            "reason": None,
            "correlation_id": "90000000-0000-0000-0000-000000000002",
        },
        {
            "id": "70000000-0000-0000-0000-000000000002",
            "event_time": now - timedelta(hours=17, minutes=55),
            "actor_user_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "actor_sub": None,
            "tenant_id": "tenant_alpha",
            "action": "export.completed",
            "target_type": "export_job",
            "target_id": "10000000-0000-0000-0000-000000000002",
            "outcome": "success",
            "reason": None,
            "correlation_id": "90000000-0000-0000-0000-000000000002",
        },
        {
            "id": "70000000-0000-0000-0000-000000000003",
            "event_time": now - timedelta(hours=5),
            "actor_user_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "actor_sub": "22222222-2222-2222-2222-222222222222",
            "tenant_id": "tenant_beta",
            "action": "export.requested",
            "target_type": "export_job",
            "target_id": "20000000-0000-0000-0000-000000000003",
            "outcome": "success",
            "reason": None,
            "correlation_id": "90000000-0000-0000-0000-000000000005",
        },
        {
            "id": "70000000-0000-0000-0000-000000000004",
            "event_time": now - timedelta(hours=4, minutes=43),
            "actor_user_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "actor_sub": None,
            "tenant_id": "tenant_beta",
            "action": "export.failed",
            "target_type": "export_job",
            "target_id": "20000000-0000-0000-0000-000000000003",
            "outcome": "failed",
            "reason": "MinIO upload failed after 2 retries: PutObject to bucket exports returned HTTP 503 Service Unavailable",
            "correlation_id": "90000000-0000-0000-0000-000000000005",
        },
    )


def seed_dev_data() -> None:
    settings = get_settings()
    if settings.environment != "local":
        raise RuntimeError("dev seed data is only supported when APP_ENV=local")
    try:
        verify_required_tables_exist()
    except RuntimeError as exc:
        raise RuntimeError(
            "required tables for dev seed data do not exist yet; database bootstrap did not complete"
        ) from exc

    now = datetime.now(timezone.utc)
    jobs = _job_seed_rows(now)
    audit_events = _audit_seed_rows(now)
    logger.info("seed started")

    with get_db_connection() as conn, conn.cursor() as cur:
        for tenant in DEMO_TENANTS:
            cur.execute(
                """
                INSERT INTO tenants (id, name, status)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET name = EXCLUDED.name,
                    status = EXCLUDED.status,
                    updated_at = NOW()
                """,
                (tenant["id"], tenant["name"], tenant["status"]),
            )

        for user in DEMO_USERS:
            cur.execute(
                """
                INSERT INTO users (id, keycloak_sub, username, email, status)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET keycloak_sub = EXCLUDED.keycloak_sub,
                    username = EXCLUDED.username,
                    email = EXCLUDED.email,
                    status = EXCLUDED.status,
                    updated_at = NOW()
                """,
                (
                    user["id"],
                    user["keycloak_sub"],
                    user["username"],
                    user["email"],
                    user["status"],
                ),
            )

        for membership in DEMO_MEMBERSHIPS:
            cur.execute(
                """
                INSERT INTO memberships (id, user_id, tenant_id, role, status)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id, tenant_id) DO UPDATE
                SET role = EXCLUDED.role,
                    status = EXCLUDED.status,
                    updated_at = NOW()
                """,
                (
                    membership["id"],
                    membership["user_id"],
                    membership["tenant_id"],
                    membership["role"],
                    membership["status"],
                ),
            )

        for record in DEMO_TENANT_RECORDS:
            cur.execute(
                """
                INSERT INTO tenant_records (
                    tenant_id,
                    account_name,
                    plan_name,
                    monthly_spend,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (tenant_id, account_name) DO UPDATE
                SET plan_name = EXCLUDED.plan_name,
                    monthly_spend = EXCLUDED.monthly_spend,
                    created_at = EXCLUDED.created_at
                """,
                (
                    record["tenant_id"],
                    record["account_name"],
                    record["plan_name"],
                    record["monthly_spend"],
                    _utc(record["created_at"]),
                ),
            )

        for job in jobs:
            cur.execute(
                """
                INSERT INTO export_jobs (
                    id,
                    tenant_id,
                    requester_user_id,
                    requester_role,
                    status,
                    object_key,
                    error_message,
                    failure_stage,
                    correlation_id,
                    retry_count,
                    created_at,
                    updated_at,
                    started_at,
                    completed_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET tenant_id = EXCLUDED.tenant_id,
                    requester_user_id = EXCLUDED.requester_user_id,
                    requester_role = EXCLUDED.requester_role,
                    status = EXCLUDED.status,
                    object_key = EXCLUDED.object_key,
                    error_message = EXCLUDED.error_message,
                    failure_stage = EXCLUDED.failure_stage,
                    correlation_id = EXCLUDED.correlation_id,
                    retry_count = EXCLUDED.retry_count,
                    created_at = EXCLUDED.created_at,
                    updated_at = EXCLUDED.updated_at,
                    started_at = EXCLUDED.started_at,
                    completed_at = EXCLUDED.completed_at
                """,
                (
                    UUID(str(job["id"])),
                    job["tenant_id"],
                    UUID(str(job["requester_user_id"])),
                    job["requester_role"],
                    job["status"],
                    job["object_key"],
                    job["error_message"],
                    job["failure_stage"],
                    UUID(str(job["correlation_id"])),
                    job["retry_count"],
                    job["created_at"],
                    job["updated_at"],
                    job["started_at"],
                    job["completed_at"],
                ),
            )

        for event in audit_events:
            cur.execute(
                """
                INSERT INTO audit_events (
                    id,
                    event_time,
                    actor_user_id,
                    actor_sub,
                    tenant_id,
                    action,
                    target_type,
                    target_id,
                    outcome,
                    reason,
                    correlation_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET event_time = EXCLUDED.event_time,
                    actor_user_id = EXCLUDED.actor_user_id,
                    actor_sub = EXCLUDED.actor_sub,
                    tenant_id = EXCLUDED.tenant_id,
                    action = EXCLUDED.action,
                    target_type = EXCLUDED.target_type,
                    target_id = EXCLUDED.target_id,
                    outcome = EXCLUDED.outcome,
                    reason = EXCLUDED.reason,
                    correlation_id = EXCLUDED.correlation_id
                """,
                (
                    UUID(str(event["id"])),
                    event["event_time"],
                    UUID(event["actor_user_id"]) if event["actor_user_id"] else None,
                    event["actor_sub"],
                    event["tenant_id"],
                    event["action"],
                    event["target_type"],
                    event["target_id"],
                    event["outcome"],
                    event["reason"],
                    UUID(str(event["correlation_id"])),
                ),
            )

        conn.commit()

    logger.info(
        "seed completed",
        extra={
            "tenants": len(DEMO_TENANTS),
            "users": len(DEMO_USERS),
            "memberships": len(DEMO_MEMBERSHIPS),
            "tenant_records": len(DEMO_TENANT_RECORDS),
            "jobs": len(jobs),
            "audit_events": len(audit_events),
        },
    )


def ensure_dev_seed_data() -> None:
    settings = get_settings()
    if not (settings.environment == "local" and settings.dev_seed_enabled):
        return
    seed_dev_data()


def main() -> None:
    bootstrap_database()
    seed_dev_data()
    print("Local demo seed data applied.")


if __name__ == "__main__":
    main()
