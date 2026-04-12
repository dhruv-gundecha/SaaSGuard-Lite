import time
from contextlib import contextmanager
from typing import Iterator
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


def create_job(*, tenant_id: str, requester_user_id: str) -> dict:
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO export_jobs (tenant_id, requester_user_id, status)
            VALUES (%s, %s, 'queued')
            RETURNING id, tenant_id, requester_user_id, status, object_key, error_message,
                      created_at, updated_at
            """,
            (tenant_id, requester_user_id),
        )
        job = cur.fetchone()
        conn.commit()
        return job


def get_job(job_id: UUID) -> dict | None:
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, tenant_id, requester_user_id, status, object_key, error_message,
                   created_at, updated_at
            FROM export_jobs
            WHERE id = %s
            """,
            (job_id,),
        )
        return cur.fetchone()


def set_job_status(
    job_id: UUID,
    *,
    status: str,
    object_key: str | None = None,
    error_message: str | None = None,
) -> None:
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE export_jobs
            SET status = %s,
                object_key = %s,
                error_message = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (status, object_key, error_message, job_id),
        )
        conn.commit()


def fetch_tenant_records(tenant_id: str) -> list[dict]:
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
