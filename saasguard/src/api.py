import logging
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, status

from src.auth import AuthenticatedUser, get_current_user
from src.db import create_job, get_job
from src.logging_utils import configure_logging
from src.tasks import export_job


configure_logging()
logger = logging.getLogger("saasguard.api")
app = FastAPI(title="SaaSGuard-Lite")


@app.get("/health")
def healthcheck() -> dict:
    return {"status": "ok"}


@app.post("/exports", status_code=status.HTTP_202_ACCEPTED)
def create_export(user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    job = create_job(tenant_id=user.tenant_id, requester_user_id=user.user_id)
    export_job.delay(str(job["id"]))

    logger.info(
        "export job created",
        extra={
            "job_id": str(job["id"]),
            "tenant_id": job["tenant_id"],
            "requester_user_id": job["requester_user_id"],
        },
    )

    return {
        "job_id": str(job["id"]),
        "status": job["status"],
        "tenant_id": job["tenant_id"],
    }


@app.get("/jobs/{job_id}")
def read_job(
    job_id: UUID, user: AuthenticatedUser = Depends(get_current_user)
) -> dict:
    job = get_job(job_id)
    if not job or job["tenant_id"] != user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    logger.info(
        "job inspected",
        extra={
            "job_id": str(job["id"]),
            "tenant_id": job["tenant_id"],
            "requester_user_id": user.user_id,
        },
    )

    return {
        "job_id": str(job["id"]),
        "tenant_id": job["tenant_id"],
        "requester_user_id": job["requester_user_id"],
        "status": job["status"],
        "object_key": job["object_key"],
        "error_message": job["error_message"],
        "created_at": job["created_at"],
        "updated_at": job["updated_at"],
    }
