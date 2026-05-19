ALTER TABLE users
ADD COLUMN IF NOT EXISTS internal_role TEXT
CHECK (internal_role IN ('soc_admin', 'ops_admin'));
