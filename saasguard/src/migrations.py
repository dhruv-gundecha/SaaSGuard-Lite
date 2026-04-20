import logging
from pathlib import Path

from src.db import get_db_connection


MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "sql" / "migrations"
REQUIRED_APP_TABLES = (
    "tenants",
    "users",
    "memberships",
    "tenant_records",
    "export_jobs",
    "audit_events",
)
logger = logging.getLogger("saasguard.bootstrap")


def wait_for_database() -> None:
    with get_db_connection():
        logger.info("database reachable")


def get_required_table_names() -> tuple[str, ...]:
    return REQUIRED_APP_TABLES


def verify_required_tables_exist(required_tables: tuple[str, ...] | None = None) -> tuple[str, ...]:
    expected = required_tables or REQUIRED_APP_TABLES
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = ANY(%s)
            ORDER BY table_name
            """,
            (list(expected),),
        )
        present = {row["table_name"] for row in cur.fetchall()}

    missing = tuple(table for table in expected if table not in present)
    if missing:
        raise RuntimeError(
            "database bootstrap incomplete: required tables missing after migrations: "
            + ", ".join(missing)
        )
    return expected


def run_migrations() -> None:
    migration_paths = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not migration_paths:
        raise RuntimeError(
            f"database bootstrap failed: no SQL migration files found in {MIGRATIONS_DIR}"
        )

    logger.info(
        "migrations started",
        extra={
            "migrations_dir": str(MIGRATIONS_DIR),
            "migration_count": len(migration_paths),
        },
    )
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute("SELECT pg_advisory_lock(8642031)")
        try:
            for path in migration_paths:
                cur.execute(
                    "SELECT 1 FROM schema_migrations WHERE version = %s", (path.name,)
                )
                if cur.fetchone():
                    continue

                cur.execute(path.read_text())
                cur.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)", (path.name,)
                )
            conn.commit()
        finally:
            cur.execute("SELECT pg_advisory_unlock(8642031)")
    logger.info("migrations completed")


def bootstrap_database() -> None:
    wait_for_database()
    run_migrations()
    verified = verify_required_tables_exist()
    logger.info(
        "required tables verified",
        extra={"required_tables": ",".join(verified)},
    )
