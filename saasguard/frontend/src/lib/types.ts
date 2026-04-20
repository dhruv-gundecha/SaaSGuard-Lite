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
  tenant_id: string;
  tenant_name: string;
  summary: {
    queued_jobs: number;
    failed_jobs: number;
    upload_failures_last_24h: number;
    completed_jobs_last_24h: number;
    authorization_denials_last_24h: number;
  };
  global_queue: {
    queued_jobs: number;
    oldest_pending_job_age_seconds: number;
  };
  links: {
    grafana: string;
    prometheus: string;
    loki: string;
    minio_console: string;
  };
}

export interface CreateExportResponse {
  job_id: string;
  status: JobStatus;
  tenant_id: string;
  correlation_id: string;
}
