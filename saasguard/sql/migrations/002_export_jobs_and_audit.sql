CREATE TABLE IF NOT EXISTS export_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL REFERENCES tenants (id),
    requester_user_id UUID NOT NULL REFERENCES users (id),
    requester_role TEXT NOT NULL CHECK (requester_role IN ('viewer', 'analyst', 'tenant_admin')),
    status TEXT NOT NULL CHECK (status IN ('queued', 'retry_pending', 'processing', 'completed', 'failed')),
    object_key TEXT,
    error_message TEXT,
    failure_stage TEXT,
    correlation_id UUID NOT NULL,
    retry_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_export_jobs_tenant_status ON export_jobs (tenant_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_export_jobs_correlation_id ON export_jobs (correlation_id);

CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_user_id UUID REFERENCES users (id),
    actor_sub TEXT,
    tenant_id TEXT REFERENCES tenants (id),
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT,
    outcome TEXT NOT NULL,
    reason TEXT,
    correlation_id UUID NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_events_time ON audit_events (event_time DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_tenant_time ON audit_events (tenant_id, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_action_time ON audit_events (action, event_time DESC);
