import csv
import io
import logging
from uuid import UUID

from src.db import fetch_tenant_records, get_job, set_job_status
from src.logging_utils import configure_logging
from src.storage import upload_csv
from src.worker_app import celery_app


configure_logging()
logger = logging.getLogger("saasguard.worker")


@celery_app.task(name="src.tasks.export_job")
def export_job(job_id: str) -> None:
    parsed_job_id = UUID(job_id)
    job = get_job(parsed_job_id)
    if not job:
        logger.error("job record not found", extra={"job_id": job_id})
        return

    log_context = {
        "job_id": str(job["id"]),
        "tenant_id": job["tenant_id"],
        "requester_user_id": job["requester_user_id"],
    }

    try:
        set_job_status(parsed_job_id, status="processing")
        logger.info("starting export", extra=log_context)

        rows = fetch_tenant_records(job["tenant_id"])
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "id",
                "tenant_id",
                "account_name",
                "plan_name",
                "monthly_spend",
                "created_at",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

        object_key = f"exports/{job['tenant_id']}/{job['id']}.csv"
        upload_csv(object_key, output.getvalue().encode("utf-8"))
        set_job_status(parsed_job_id, status="completed", object_key=object_key)
        logger.info("export completed", extra=log_context)
    except Exception as exc:
        set_job_status(parsed_job_id, status="failed", error_message=str(exc))
        logger.exception("export failed", extra=log_context)
        raise
