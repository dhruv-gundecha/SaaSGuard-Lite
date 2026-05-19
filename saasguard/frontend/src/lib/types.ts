export type Role = "viewer" | "analyst" | "tenant_admin";
export type JobStatus =
  | "queued"
  | "retry_pending"
  | "processing"
  | "completed"
  | "failed";

export interface Membership {
  tenant_id: string;
  tenant_name: string;
  role: Role;
}

export interface SessionUser {
  id: string;
  keycloak_sub: string;
  username: string;
  email: string | null;
}

export interface SessionResponse {
  user: SessionUser;
  active_tenant: Membership | null;
  memberships: Membership[];
}

export interface ExportJob {
  job_id: string;
  tenant_id: string;
  requester_user_id: string;
  requester_username?: string;
  requester_role: Role;
  status: JobStatus;
  object_key: string | null;
  error_message: string | null;
  failure_stage?: string | null;
  correlation_id: string;
  retry_count: number;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface JobsResponse {
  tenant_id: string;
  count: number;
  items: ExportJob[];
}

export interface AuditEvent {
  id: string;
  event_time: string;
  actor_user_id: string | null;
  actor_sub: string | null;
  tenant_id: string | null;
  action: string;
  target_type: string;
  target_id: string | null;
  outcome: string;
  reason: string | null;
  correlation_id: string;
}

export interface AuditResponse {
  tenant_id: string;
  events: AuditEvent[];
}

export interface OperationsSummaryResponse {
  generated_at: string;
  scope: {
    tenant_id: string;
    tenant_name: string;
    role: Role;
  };
  overall_status: "healthy" | "degraded" | "unhealthy";
  api: {
    status: "healthy" | "degraded" | "unhealthy";
    window_minutes: number;
    request_count: number;
    request_rate: number;
    error_count: number;
    error_rate: number;
    auth_failure_count: number;
    authorization_denial_count: number;
    p95_latency_ms: number;
    impact: string;
  };
  exports: {
    status: "healthy" | "degraded" | "unhealthy";
    queued: number;
    retry_pending: number;
    processing: number;
    completed_last_hour: number;
    failed_last_hour: number;
    oldest_pending_age_seconds: number;
    impact: string;
  };
  worker: {
    status: "healthy" | "degraded" | "unhealthy";
    jobs_started: number;
    jobs_completed: number;
    jobs_failed: number;
    retry_count: number;
    minio_upload_failures: number;
    db_query_failures: number;
    jobs_started_last_hour: number;
    jobs_failed_last_hour: number;
    retries_last_hour: number;
    impact: string;
  };
  security: {
    status: "healthy" | "degraded" | "unhealthy";
    auth_failures: number;
    authorization_denials: number;
    cross_tenant_denials: number;
    impact: string;
  };
  dependencies: {
    status: "healthy" | "degraded" | "unhealthy";
    postgres: {
      status: "healthy" | "degraded" | "unhealthy";
      latency_ms: number | null;
      reason: string;
    };
    redis: {
      status: "healthy" | "degraded" | "unhealthy";
      latency_ms: number | null;
      reason: string;
    };
    minio: {
      status: "healthy" | "degraded" | "unhealthy";
      latency_ms: number | null;
      reason: string;
    };
    keycloak: {
      status: "healthy" | "degraded" | "unhealthy";
      latency_ms: number | null;
      reason: string;
    };
  };
  deployment: {
    status: "healthy" | "degraded" | "unhealthy";
    suspected_regression: boolean;
    impact: string;
  };
  links: {
    grafana: string;
    grafana_service_health: string;
    grafana_tenant_impact: string;
    grafana_auth_security: string;
    prometheus: string;
    loki: string;
    uptime_kuma: string;
    minio_console: string;
  };
}

export interface CreateExportResponse {
  job_id: string;
  status: JobStatus;
  tenant_id: string;
  correlation_id: string;
}
