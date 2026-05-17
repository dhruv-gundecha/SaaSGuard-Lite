import time
from contextlib import contextmanager
from typing import Any, Iterator
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from src.config import get_settings


@contextmanager
def get_db_connection() -> Iterator[psycopg.Connection]:
    conn = None
    last_error = None
    for _ in range(10):
        try:
            conn = psycopg.connect(get_settings().postgres_dsn, row_factory=dict_row)
            break
        except psycopg.OperationalError as exc:
            last_error = exc
            time.sleep(1)

    if conn is None:
        raise last_error or RuntimeError("database connection failed")

    try:
        yield conn
    finally:
        conn.close()


def resolve_user_by_identity(
    *, keycloak_sub: str, username: str | None, email: str | None
) -> dict[str, Any] | None:
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE users
            SET username = COALESCE(%s, username),
                email = COALESCE(%s, email),
                updated_at = NOW()
            WHERE keycloak_sub = %s
              AND status = 'active'
            RETURNING id, keycloak_sub, username, email, status, created_at, updated_at
            """,
            (username, email, keycloak_sub),
        )
        user = cur.fetchone()
        if user:
            conn.commit()
            return user

        settings = get_settings()
        if (
            settings.environment == "local"
            and settings.dev_auth_username_fallback_enabled
            and username
        ):
            cur.execute(
                """
                UPDATE users
                SET keycloak_sub = %s,
                    email = COALESCE(%s, email),
                    updated_at = NOW()
                WHERE username = %s
                  AND status = 'active'
                RETURNING id, keycloak_sub, username, email, status, created_at, updated_at
                """,
                (keycloak_sub, email, username),
            )
            user = cur.fetchone()
        conn.commit()
        return user


def get_active_memberships_for_user(user_id: str) -> list[dict[str, Any]]:
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT m.id, m.user_id, m.tenant_id, m.role, m.status, t.name AS tenant_name
            FROM memberships m
            JOIN tenants t ON t.id = m.tenant_id
            WHERE m.user_id = %s
              AND m.status = 'active'
              AND t.status = 'active'
            ORDER BY m.tenant_id
            """,
            (user_id,),
        )
        return list(cur.fetchall())


def get_membership_for_user_and_tenant(user_id: str, tenant_id: str) -> dict[str, Any] | None:
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT m.id, m.user_id, m.tenant_id, m.role, m.status, t.name AS tenant_name
            FROM memberships m
            JOIN tenants t ON t.id = m.tenant_id
            WHERE m.user_id = %s
              AND m.tenant_id = %s
              AND m.status = 'active'
              AND t.status = 'active'
            """,
            (user_id, tenant_id),
        )
        return cur.fetchone()


def create_job(
    *,
    tenant_id: str,
    requester_user_id: str,
    requester_role: str,
    correlation_id: str,
) -> dict[str, Any]:
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO export_jobs (
                tenant_id,
                requester_user_id,
                requester_role,
                status,
                correlation_id
            )
            VALUES (%s, %s, %s, 'queued', %s)
            RETURNING id, tenant_id, requester_user_id, requester_role, status, object_key,
                      error_message, failure_stage, correlation_id, retry_count,
                      created_at, updated_at, started_at, completed_at
            """,
            (tenant_id, requester_user_id, requester_role, correlation_id),
        )
        job = cur.fetchone()
        conn.commit()
        return job


def get_job(job_id: UUID) -> dict[str, Any] | None:
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, tenant_id, requester_user_id, requester_role, status, object_key,
                   error_message, failure_stage, correlation_id, retry_count,
                   created_at, updated_at, started_at, completed_at
            FROM export_jobs
            WHERE id = %s
            """,
            (job_id,),
        )
        return cur.fetchone()


def get_job_for_tenant(job_id: UUID, tenant_id: str) -> dict[str, Any] | None:
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, tenant_id, requester_user_id, requester_role, status, object_key,
                   error_message, failure_stage, correlation_id, retry_count,
                   created_at, updated_at, started_at, completed_at
            FROM export_jobs
            WHERE id = %s
              AND tenant_id = %s
            """,
            (job_id, tenant_id),
        )
        return cur.fetchone()


def list_jobs_for_tenant(
    *,
    tenant_id: str,
    status: str | None = None,
    hours: int = 168,
    limit: int = 100,
) -> list[dict[str, Any]]:
    query = """
        SELECT j.id, j.tenant_id, j.requester_user_id, u.username AS requester_username,
               j.requester_role, j.status, j.object_key, j.error_message, j.failure_stage,
               j.correlation_id, j.retry_count, j.created_at, j.updated_at, j.started_at,
               j.completed_at
        FROM export_jobs j
        JOIN users u ON u.id = j.requester_user_id
        WHERE j.tenant_id = %s
          AND j.created_at >= NOW() - (%s * INTERVAL '1 hour')
    """
    params: list[Any] = [tenant_id, hours]

    if status is not None:
        query += " AND j.status = %s"
        params.append(status)

    query += """
        ORDER BY j.created_at DESC
        LIMIT %s
    """
    params.append(limit)

    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(query, params)
        return list(cur.fetchall())


def claim_job_for_processing(job_id: UUID) -> dict[str, Any] | None:
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE export_jobs
            SET status = 'processing',
                started_at = COALESCE(started_at, NOW()),
                updated_at = NOW(),
                error_message = NULL,
                failure_stage = NULL
            WHERE id = %s
              AND status IN ('queued', 'retry_pending')
            RETURNING id, tenant_id, requester_user_id, requester_role, status, object_key,
                      error_message, failure_stage, correlation_id, retry_count,
                      created_at, updated_at, started_at, completed_at
            """,
            (job_id,),
        )
        job = cur.fetchone()
        conn.commit()
        return job


def mark_job_completed(job_id: UUID, *, object_key: str) -> None:
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE export_jobs
            SET status = 'completed',
                object_key = %s,
                error_message = NULL,
                failure_stage = NULL,
                completed_at = NOW(),
                updated_at = NOW()
            WHERE id = %s
              AND status = 'processing'
            """,
            (object_key, job_id),
        )
        conn.commit()


def mark_job_failed(job_id: UUID, *, error_message: str, failure_stage: str) -> None:
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE export_jobs
            SET status = 'failed',
                error_message = %s,
                failure_stage = %s,
                updated_at = NOW(),
                completed_at = NOW()
            WHERE id = %s
              AND status IN ('processing', 'retry_pending')
            """,
            (error_message, failure_stage, job_id),
        )
        conn.commit()


def append_job_retry(job_id: UUID, *, error_message: str, failure_stage: str) -> dict[str, Any] | None:
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE export_jobs
            SET status = 'retry_pending',
                error_message = %s,
                failure_stage = %s,
                retry_count = retry_count + 1,
                updated_at = NOW()
            WHERE id = %s
              AND status = 'processing'
            RETURNING id, retry_count, correlation_id, tenant_id, requester_user_id
            """,
            (error_message, failure_stage, job_id),
        )
        job = cur.fetchone()
        conn.commit()
        return job


def fetch_tenant_records(tenant_id: str) -> list[dict[str, Any]]:
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, tenant_id, account_name, plan_name, monthly_spend, created_at
            FROM tenant_records
            WHERE tenant_id = %s
            ORDER BY id
            """,
            (tenant_id,),
        )
        return list(cur.fetchall())


def record_audit_event(
    *,
    actor_user_id: str | None,
    actor_sub: str | None,
    tenant_id: str | None,
    action: str,
    target_type: str,
    target_id: str | None,
    outcome: str,
    reason: str | None,
    correlation_id: str,
) -> None:
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO audit_events (
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
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                actor_user_id,
                actor_sub,
                tenant_id,
                action,
                target_type,
                target_id,
                outcome,
                reason,
                correlation_id,
            ),
        )
        conn.commit()


def list_audit_events(*, tenant_id: str, limit: int = 50) -> list[dict[str, Any]]:
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, event_time, actor_user_id, actor_sub, tenant_id, action, target_type,
                   target_id, outcome, reason, correlation_id
            FROM audit_events
            WHERE tenant_id = %s
            ORDER BY event_time DESC
            LIMIT %s
            """,
            (tenant_id, limit),
        )
        return list(cur.fetchall())


def get_operations_summary(*, tenant_id: str) -> dict[str, Any]:
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE status IN ('queued', 'retry_pending')) AS queued_jobs,
                COUNT(*) FILTER (WHERE status = 'failed') AS failed_jobs,
                COUNT(*) FILTER (
                    WHERE status = 'failed'
                      AND failure_stage = 'upload'
                      AND created_at >= NOW() - INTERVAL '24 hours'
                ) AS upload_failures_last_24h,
                COUNT(*) FILTER (
                    WHERE status = 'completed'
                      AND created_at >= NOW() - INTERVAL '24 hours'
                ) AS completed_jobs_last_24h
            FROM export_jobs
            WHERE tenant_id = %s
            """,
            (tenant_id,),
        )
        summary = cur.fetchone() or {}
        cur.execute(
            """
            SELECT COUNT(*) AS authorization_denials_last_24h
            FROM audit_events
            WHERE tenant_id = %s
              AND outcome = 'denied'
              AND event_time >= NOW() - INTERVAL '24 hours'
            """,
            (tenant_id,),
        )
        denials = cur.fetchone() or {}
        return {
            **summary,
            **denials,
        }


def get_operations_overview(*, tenant_id: str) -> dict[str, Any]:
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE status = 'queued') AS queued_jobs,
                COUNT(*) FILTER (WHERE status = 'retry_pending') AS retry_pending_jobs,
                COUNT(*) FILTER (WHERE status = 'processing') AS processing_jobs,
                COUNT(*) FILTER (
                    WHERE status = 'completed'
                      AND completed_at >= NOW() - INTERVAL '1 hour'
                ) AS completed_jobs_last_hour,
                COUNT(*) FILTER (
                    WHERE status = 'failed'
                      AND completed_at >= NOW() - INTERVAL '1 hour'
                ) AS failed_jobs_last_hour,
                COUNT(*) FILTER (
                    WHERE started_at >= NOW() - INTERVAL '1 hour'
                ) AS jobs_started_last_hour,
                COALESCE(
                    SUM(retry_count) FILTER (
                        WHERE updated_at >= NOW() - INTERVAL '1 hour'
                    ),
                    0
                ) AS retry_count_last_hour,
                COUNT(*) FILTER (
                    WHERE status = 'failed'
                      AND failure_stage = 'upload'
                      AND completed_at >= NOW() - INTERVAL '1 hour'
                ) AS minio_upload_failures_last_hour,
                EXTRACT(
                    EPOCH FROM (
                        NOW() - MIN(created_at) FILTER (WHERE status IN ('queued', 'retry_pending'))
                    )
                ) AS oldest_pending_job_age_seconds,
                COUNT(*) FILTER (
                    WHERE tenant_id = %s
                      AND status IN ('queued', 'retry_pending')
                ) AS active_tenant_backlog
            FROM export_jobs
            """,
            (tenant_id,),
        )
        job_summary = cur.fetchone() or {}
        cur.execute(
            """
            SELECT
                COUNT(*) FILTER (
                    WHERE outcome = 'denied'
                      AND event_time >= NOW() - INTERVAL '1 hour'
                ) AS authorization_denials_last_hour,
                COUNT(*) FILTER (
                    WHERE outcome = 'denied'
                      AND reason = 'cross-tenant access denied'
                      AND event_time >= NOW() - INTERVAL '1 hour'
                ) AS cross_tenant_denials_last_hour
            FROM audit_events
            """
        )
        audit_summary = cur.fetchone() or {}
        return {
            **job_summary,
            **audit_summary,
            "oldest_pending_job_age_seconds": (
                job_summary.get("oldest_pending_job_age_seconds") or 0
            ),
            "db_query_failures_last_hour": 0,
        }


def get_worker_stats() -> dict[str, Any]:
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE status IN ('queued', 'retry_pending')) AS queued_jobs,
                EXTRACT(
                    EPOCH FROM (
                        NOW() - MIN(created_at) FILTER (WHERE status IN ('queued', 'retry_pending'))
                    )
                ) AS oldest_pending_job_age_seconds
            FROM export_jobs
            """
        )
        return cur.fetchone() or {
            "queued_jobs": 0,
            "oldest_pending_job_age_seconds": None,
        }
