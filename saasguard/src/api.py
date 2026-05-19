import logging
import time
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from src.auth import AuthenticatedUser, get_current_user
from src.authz import TenantContext, require_role, resolve_active_tenant
from src.config import get_settings
from src.context import reset_request_context, set_request_context
from src.db import (
    create_job,
    get_job,
    get_job_for_tenant,
    get_operations_summary,
    get_worker_stats,
    list_jobs_for_tenant,
    list_audit_events,
    record_audit_event,
)
from src.logging_utils import configure_logging, log_event
from src.metrics import (
    api_auth_failures_total,
    api_authorization_denials_total,
    api_export_requests_created_total,
    api_job_read_denials_total,
    api_request_latency_seconds,
    api_requests_total,
    render_metrics,
    tenant_metric_labels,
    oldest_pending_job_age_seconds,
    queue_backlog_jobs,
)
from src.migrations import bootstrap_database
from src.operations import build_operations_summary, record_api_request_observation
from src.seed_dev_data import ensure_dev_seed_data
from src.storage import create_presigned_download_url
from src.tasks import export_job


configure_logging()
logger = logging.getLogger("saasguard.api")
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    bootstrap_database()
    ensure_dev_seed_data()
    yield


app = FastAPI(title="SaaSGuard-Lite", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    correlation_id = request.headers.get("X-Correlation-ID", request_id)
    request.state.request_id = request_id
    request.state.correlation_id = correlation_id

    tokens = set_request_context(
        request_id=request_id,
        correlation_id=correlation_id,
        service="api",
    )
    started_at = time.perf_counter()
    response = None
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    try:
        response = await call_next(request)
        status_code = response.status_code
    except HTTPException as exc:
        status_code = exc.status_code
        raise
    finally:
        latency_seconds = time.perf_counter() - started_at
        api_request_latency_seconds.labels(
            method=request.method, path=request.url.path
        ).observe(latency_seconds)
        api_requests_total.labels(
            method=request.method,
            path=request.url.path,
            status_code=str(status_code),
        ).inc()
        record_api_request_observation(status_code, latency_seconds)
        if status_code == status.HTTP_401_UNAUTHORIZED:
            api_auth_failures_total.inc()
        elif status_code == status.HTTP_403_FORBIDDEN:
            api_authorization_denials_total.labels(action=request.url.path).inc()
        reset_request_context(tokens)
    if response is not None:
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def resolve_tenant_context(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    x_active_tenant: str | None = Header(default=None),
) -> tuple[AuthenticatedUser, TenantContext, str]:
    tenant = resolve_active_tenant(user, x_active_tenant)
    log_event(
        logger,
        logging.INFO,
        "auth.membership_resolved",
        "active tenant membership resolved",
        tenant_id=tenant.tenant_id,
        user_id=user.user_id,
        keycloak_sub=user.keycloak_sub,
        correlation_id=request.state.correlation_id,
        outcome="success",
    )
    return user, tenant, request.state.correlation_id


@app.get("/health")
def healthcheck() -> dict:
    return {"status": "ok"}


@app.get("/me")
def read_session(
    user: AuthenticatedUser = Depends(get_current_user),
    x_active_tenant: str | None = Header(default=None),
) -> dict:
    tenant: TenantContext | None = None
    if x_active_tenant or len(user.memberships) == 1:
        tenant = resolve_active_tenant(user, x_active_tenant)
    return {
        "user": {
            "id": user.user_id,
            "keycloak_sub": user.keycloak_sub,
            "username": user.username,
            "email": user.email,
        },
        "active_tenant": (
            {
                "tenant_id": tenant.tenant_id,
                "tenant_name": tenant.tenant_name,
                "role": tenant.role,
            }
            if tenant
            else None
        ),
        "memberships": [
            {
                "tenant_id": membership["tenant_id"],
                "tenant_name": membership["tenant_name"],
                "role": membership["role"],
            }
            for membership in user.memberships
        ],
    }


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    stats = get_worker_stats()
    queue_backlog_jobs.set(stats["queued_jobs"] or 0)
    oldest_pending_job_age_seconds.set(stats["oldest_pending_job_age_seconds"] or 0)
    payload, content_type = render_metrics()
    return PlainTextResponse(payload.decode("utf-8"), media_type=content_type)


@app.post("/exports", status_code=status.HTTP_202_ACCEPTED)
def create_export(
    context: tuple[AuthenticatedUser, TenantContext, str] = Depends(resolve_tenant_context),
) -> dict:
    user, tenant, correlation_id = context
    require_role(
        user=user,
        tenant=tenant,
        minimum_role="analyst",
        correlation_id=correlation_id,
        action="export.requested",
    )
    log_event(
        logger,
        logging.INFO,
        "export.request_received",
        "export request received",
        tenant_id=tenant.tenant_id,
        user_id=user.user_id,
        keycloak_sub=user.keycloak_sub,
        correlation_id=correlation_id,
        outcome="received",
    )

    job = create_job(
        tenant_id=tenant.tenant_id,
        requester_user_id=user.user_id,
        requester_role=tenant.role,
        correlation_id=correlation_id,
    )
    export_job.delay(str(job["id"]))
    api_export_requests_created_total.labels(
        role=tenant.role, **tenant_metric_labels(tenant.tenant_id)
    ).inc()
    record_audit_event(
        actor_user_id=user.user_id,
        actor_sub=user.keycloak_sub,
        tenant_id=tenant.tenant_id,
        action="export.requested",
        target_type="export_job",
        target_id=str(job["id"]),
        outcome="success",
        reason=None,
        correlation_id=correlation_id,
    )

    log_event(
        logger,
        logging.INFO,
        "export.job_created",
        "export job persisted",
        job_id=str(job["id"]),
        tenant_id=tenant.tenant_id,
        user_id=user.user_id,
        keycloak_sub=user.keycloak_sub,
        correlation_id=correlation_id,
        outcome="success",
    )
    log_event(
        logger,
        logging.INFO,
        "export.job_enqueued",
        "export job enqueued",
        job_id=str(job["id"]),
        tenant_id=tenant.tenant_id,
        user_id=user.user_id,
        keycloak_sub=user.keycloak_sub,
        correlation_id=correlation_id,
        outcome="success",
    )

    return {
        "job_id": str(job["id"]),
        "status": job["status"],
        "tenant_id": job["tenant_id"],
        "correlation_id": str(job["correlation_id"]),
    }


@app.get("/jobs/{job_id}")
def read_job(
    job_id: UUID,
    context: tuple[AuthenticatedUser, TenantContext, str] = Depends(resolve_tenant_context),
) -> dict:
    user, tenant, correlation_id = context
    require_role(
        user=user,
        tenant=tenant,
        minimum_role="viewer",
        correlation_id=correlation_id,
        action="job.viewed",
    )
    job = get_job_for_tenant(job_id, tenant.tenant_id)
    if not job:
        existing_job = get_job(job_id)
        if existing_job:
            api_job_read_denials_total.inc()
            record_audit_event(
                actor_user_id=user.user_id,
                actor_sub=user.keycloak_sub,
                tenant_id=tenant.tenant_id,
                action="job.viewed",
                target_type="export_job",
                target_id=str(job_id),
                outcome="denied",
                reason="cross-tenant access denied",
                correlation_id=correlation_id,
            )
            log_event(
                logger,
                logging.WARNING,
                "job.read_denied",
                "cross-tenant job read denied",
                job_id=str(job_id),
                tenant_id=tenant.tenant_id,
                user_id=user.user_id,
                keycloak_sub=user.keycloak_sub,
                correlation_id=correlation_id,
                outcome="denied",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access to this job is denied",
            )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    record_audit_event(
        actor_user_id=user.user_id,
        actor_sub=user.keycloak_sub,
        tenant_id=tenant.tenant_id,
        action="job.viewed",
        target_type="export_job",
        target_id=str(job["id"]),
        outcome="success",
        reason=None,
        correlation_id=correlation_id,
    )
    log_event(
        logger,
        logging.INFO,
        "job.read_allowed",
        "job read allowed",
        job_id=str(job["id"]),
        tenant_id=tenant.tenant_id,
        user_id=user.user_id,
        keycloak_sub=user.keycloak_sub,
        correlation_id=correlation_id,
        outcome="success",
    )

    return {
        "job_id": str(job["id"]),
        "tenant_id": job["tenant_id"],
        "requester_user_id": str(job["requester_user_id"]),
        "requester_role": job["requester_role"],
        "status": job["status"],
        "object_key": job["object_key"],
        "error_message": job["error_message"],
        "failure_stage": job["failure_stage"],
        "correlation_id": str(job["correlation_id"]),
        "retry_count": job["retry_count"],
        "created_at": job["created_at"],
        "updated_at": job["updated_at"],
        "started_at": job["started_at"],
        "completed_at": job["completed_at"],
    }


@app.get("/jobs")
def list_jobs(
    status_filter: str | None = Query(default=None, alias="status"),
    hours: int = Query(default=168, ge=1, le=720),
    limit: int = Query(default=100, ge=1, le=200),
    context: tuple[AuthenticatedUser, TenantContext, str] = Depends(resolve_tenant_context),
) -> dict:
    user, tenant, correlation_id = context
    normalized_status = status_filter or None
    require_role(
        user=user,
        tenant=tenant,
        minimum_role="viewer",
        correlation_id=correlation_id,
        action="job.listed",
    )
    jobs = list_jobs_for_tenant(
        tenant_id=tenant.tenant_id,
        status=normalized_status,
        hours=hours,
        limit=limit,
    )
    return {
        "tenant_id": tenant.tenant_id,
        "count": len(jobs),
        "items": [
            {
                "job_id": str(job["id"]),
                "tenant_id": job["tenant_id"],
                "requester_user_id": str(job["requester_user_id"]),
                "requester_username": job["requester_username"],
                "requester_role": job["requester_role"],
                "status": job["status"],
                "object_key": job["object_key"],
                "error_message": job["error_message"],
                "failure_stage": job["failure_stage"],
                "correlation_id": str(job["correlation_id"]),
                "retry_count": job["retry_count"],
                "created_at": job["created_at"],
                "updated_at": job["updated_at"],
                "started_at": job["started_at"],
                "completed_at": job["completed_at"],
            }
            for job in jobs
        ],
    }


@app.get("/jobs/{job_id}/download")
def download_export(
    job_id: UUID,
    context: tuple[AuthenticatedUser, TenantContext, str] = Depends(resolve_tenant_context),
) -> dict:
    user, tenant, correlation_id = context
    require_role(
        user=user,
        tenant=tenant,
        minimum_role="viewer",
        correlation_id=correlation_id,
        action="export.downloaded",
    )
    job = get_job_for_tenant(job_id, tenant.tenant_id)
    if not job or job["status"] != "completed" or not job["object_key"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Completed export not found",
        )

    record_audit_event(
        actor_user_id=user.user_id,
        actor_sub=user.keycloak_sub,
        tenant_id=tenant.tenant_id,
        action="export.downloaded",
        target_type="export_job",
        target_id=str(job["id"]),
        outcome="success",
        reason=None,
        correlation_id=correlation_id,
    )
    return {
        "job_id": str(job["id"]),
        "download_url": create_presigned_download_url(job["object_key"]),
        "expires_in_seconds": settings.minio_presign_expiry_seconds,
    }


@app.get("/audit-events")
def read_audit_events(
    limit: int = Query(default=50, ge=1, le=200),
    context: tuple[AuthenticatedUser, TenantContext, str] = Depends(resolve_tenant_context),
) -> dict:
    user, tenant, correlation_id = context
    require_role(
        user=user,
        tenant=tenant,
        minimum_role="tenant_admin",
        correlation_id=correlation_id,
        action="audit.viewed",
    )
    events = list_audit_events(tenant_id=tenant.tenant_id, limit=limit)
    return {"tenant_id": tenant.tenant_id, "events": events}


@app.get("/operations/summary")
def read_operations_summary(
    context: tuple[AuthenticatedUser, TenantContext, str] = Depends(resolve_tenant_context),
) -> dict:
    user, tenant, correlation_id = context
    require_role(
        user=user,
        tenant=tenant,
        minimum_role="viewer",
        correlation_id=correlation_id,
        action="operations.viewed",
    )
    return build_operations_summary(
        tenant_id=tenant.tenant_id,
        tenant_name=tenant.tenant_name,
        role=tenant.role,
    )
