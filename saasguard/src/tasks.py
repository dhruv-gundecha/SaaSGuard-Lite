import csv
import io
import logging
from datetime import datetime, timezone
from uuid import UUID

from botocore.exceptions import BotoCoreError, ClientError
from celery.exceptions import Retry

from src.config import get_settings
from src.context import reset_request_context, set_request_context
from src.db import (
    append_job_retry,
    claim_job_for_processing,
    fetch_tenant_records,
    get_job,
    mark_job_completed,
    mark_job_failed,
    record_audit_event,
)
from src.logging_utils import configure_logging, log_event
from src.metrics import (
    tenant_metric_labels,
    worker_db_query_failures_total,
    worker_export_row_count,
    worker_job_duration_seconds,
    worker_job_retries_total,
    worker_jobs_completed_total,
    worker_jobs_failed_total,
    worker_jobs_started_total,
    worker_minio_upload_failures_total,
    worker_queue_wait_seconds,
)
from src.storage import upload_csv
from src.celery_app import celery_app


configure_logging()
logger = logging.getLogger("saasguard.worker")
settings = get_settings()


class TransientJobFailure(Exception):
    def __init__(self, stage: str, message: str) -> None:
        super().__init__(message)
        self.stage = stage


class PermanentJobFailure(Exception):
    def __init__(self, stage: str, message: str) -> None:
        super().__init__(message)
        self.stage = stage


def _job_log_fields(job: dict) -> dict[str, str]:
    return {
        "job_id": str(job["id"]),
        "tenant_id": job["tenant_id"],
        "user_id": str(job["requester_user_id"]),
        "correlation_id": str(job["correlation_id"]),
    }


@celery_app.task(
    bind=True,
    name="src.tasks.export_job",
    max_retries=get_settings().worker_retry_limit,
)
def export_job(self, job_id: str) -> None:
    parsed_job_id = UUID(job_id)
    job = get_job(parsed_job_id)
    if not job:
        worker_db_query_failures_total.labels(operation="get_job_missing").inc()
        log_event(
            logger,
            logging.ERROR,
            "worker.job_received",
            "job record not found",
            job_id=job_id,
            outcome="failed",
            error_type="JobNotFound",
        )
        return

    tokens = set_request_context(
        correlation_id=str(job["correlation_id"]),
        service="worker",
    )
    try:
        log_fields = _job_log_fields(job)
        log_event(
            logger,
            logging.INFO,
            "worker.job_received",
            "worker received job identifier",
            **log_fields,
            outcome="received",
        )

        claimed_job = claim_job_for_processing(parsed_job_id)
        if not claimed_job:
            log_event(
                logger,
                logging.INFO,
                "worker.job_loaded",
                "job was not runnable and will be skipped",
                **log_fields,
                outcome="skipped",
            )
            return

        metric_labels = tenant_metric_labels(claimed_job["tenant_id"])
        worker_jobs_started_total.labels(**metric_labels).inc()
        if claimed_job["started_at"]:
            queue_wait = (
                claimed_job["started_at"] - claimed_job["created_at"]
            ).total_seconds()
            worker_queue_wait_seconds.labels(**metric_labels).observe(max(queue_wait, 0))

        log_fields = _job_log_fields(claimed_job)
        log_event(
            logger,
            logging.INFO,
            "worker.job_loaded",
            "job loaded from authoritative database state",
            **log_fields,
            outcome="success",
        )
        log_event(
            logger,
            logging.INFO,
            "worker.context_resolved",
            "trusted tenant context resolved from job record",
            **log_fields,
            outcome="success",
        )

        started_at = datetime.now(timezone.utc)
        log_event(
            logger,
            logging.INFO,
            "worker.export.started",
            "tenant export started",
            **log_fields,
            outcome="started",
        )

        try:
            rows = fetch_tenant_records(claimed_job["tenant_id"])
        except Exception as exc:
            worker_db_query_failures_total.labels(operation="fetch_tenant_records").inc()
            raise TransientJobFailure("records_load", "failed to load tenant export rows") from exc

        worker_export_row_count.labels(**metric_labels).observe(len(rows))
        log_event(
            logger,
            logging.INFO,
            "worker.export.records_loaded",
            "tenant-scoped export rows loaded",
            **log_fields,
            outcome="success",
        )

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

        object_key = f"exports/{claimed_job['tenant_id']}/{claimed_job['id']}.csv"
        try:
            log_event(
                logger,
                logging.INFO,
                "worker.export.upload_started",
                "object upload started",
                **log_fields,
                outcome="started",
            )
            upload_csv(object_key, output.getvalue().encode("utf-8"))
        except (BotoCoreError, ClientError) as exc:
            worker_minio_upload_failures_total.inc()
            log_event(
                logger,
                logging.ERROR,
                "worker.export.upload_failed",
                "object upload failed",
                **log_fields,
                outcome="failed",
                error_type=type(exc).__name__,
                error_message="failed to upload export object",
            )
            raise TransientJobFailure("upload", "failed to upload export object") from exc

        mark_job_completed(parsed_job_id, object_key=object_key)
        worker_jobs_completed_total.labels(**metric_labels).inc()
        worker_job_duration_seconds.labels(**metric_labels).observe(
            (datetime.now(timezone.utc) - started_at).total_seconds()
        )
        record_audit_event(
            actor_user_id=str(claimed_job["requester_user_id"]),
            actor_sub=None,
            tenant_id=claimed_job["tenant_id"],
            action="export.completed",
            target_type="export_job",
            target_id=str(claimed_job["id"]),
            outcome="success",
            reason=None,
            correlation_id=str(claimed_job["correlation_id"]),
        )
        log_event(
            logger,
            logging.INFO,
            "worker.export.completed",
            "tenant export completed",
            **log_fields,
            outcome="success",
        )
    except TransientJobFailure as exc:
        retry_state = append_job_retry(
            parsed_job_id,
            error_message=str(exc),
            failure_stage=exc.stage,
        )
        metric_labels = tenant_metric_labels(job["tenant_id"])
        if retry_state and retry_state["retry_count"] <= settings.worker_retry_limit:
            worker_job_retries_total.labels(stage=exc.stage, **metric_labels).inc()
            log_event(
                logger,
                logging.WARNING,
                "worker.job_retried",
                "transient job failure scheduled for retry",
                **_job_log_fields(job),
                outcome="retrying",
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            raise self.retry(countdown=settings.worker_retry_delay_seconds, exc=exc)
        mark_job_failed(parsed_job_id, error_message=str(exc), failure_stage=exc.stage)
        worker_jobs_failed_total.labels(stage=exc.stage, **metric_labels).inc()
        record_audit_event(
            actor_user_id=str(job["requester_user_id"]),
            actor_sub=None,
            tenant_id=job["tenant_id"],
            action="export.failed",
            target_type="export_job",
            target_id=str(job["id"]),
            outcome="failed",
            reason=str(exc),
            correlation_id=str(job["correlation_id"]),
        )
        log_event(
            logger,
            logging.ERROR,
            "worker.job_failed",
            "retry limit exceeded for transient failure",
            **_job_log_fields(job),
            outcome="failed",
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
    except PermanentJobFailure as exc:
        metric_labels = tenant_metric_labels(job["tenant_id"])
        worker_jobs_failed_total.labels(stage=exc.stage, **metric_labels).inc()
        mark_job_failed(parsed_job_id, error_message=str(exc), failure_stage=exc.stage)
        record_audit_event(
            actor_user_id=str(job["requester_user_id"]),
            actor_sub=None,
            tenant_id=job["tenant_id"],
            action="export.failed",
            target_type="export_job",
            target_id=str(job["id"]),
            outcome="failed",
            reason=str(exc),
            correlation_id=str(job["correlation_id"]),
        )
        log_event(
            logger,
            logging.ERROR,
            "worker.job_failed",
            "permanent job failure recorded",
            **_job_log_fields(job),
            outcome="failed",
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
    except Retry:
        raise
    except Exception as exc:
        metric_labels = tenant_metric_labels(job["tenant_id"])
        worker_jobs_failed_total.labels(stage="unexpected", **metric_labels).inc()
        mark_job_failed(
            parsed_job_id,
            error_message="unexpected worker failure",
            failure_stage="unexpected",
        )
        record_audit_event(
            actor_user_id=str(job["requester_user_id"]),
            actor_sub=None,
            tenant_id=job["tenant_id"],
            action="export.failed",
            target_type="export_job",
            target_id=str(job["id"]),
            outcome="failed",
            reason="unexpected worker failure",
            correlation_id=str(job["correlation_id"]),
        )
        log_event(
            logger,
            logging.ERROR,
            "worker.job_failed",
            "unexpected job failure recorded",
            **_job_log_fields(job),
            outcome="failed",
            error_type=type(exc).__name__,
            error_message="unexpected worker failure",
        )
        raise
    finally:
        reset_request_context(tokens)
