CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS tenant_records (
    id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    account_name TEXT NOT NULL,
    plan_name TEXT NOT NULL,
    monthly_spend NUMERIC(10,2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS export_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    requester_user_id TEXT NOT NULL,
    status TEXT NOT NULL,
    object_key TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO tenant_records (tenant_id, account_name, plan_name, monthly_spend)
VALUES
    ('tenant_alpha', 'Acme Corp', 'starter', 120.00),
    ('tenant_alpha', 'Acme Corp - Sandbox', 'growth', 480.00),
    ('tenant_beta', 'Globex', 'starter', 95.00),
    ('tenant_beta', 'Globex EU', 'enterprise', 1250.00)
ON CONFLICT DO NOTHING;
