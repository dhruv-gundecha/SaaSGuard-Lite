CREATE UNIQUE INDEX IF NOT EXISTS idx_tenant_records_tenant_account
ON tenant_records (tenant_id, account_name);
