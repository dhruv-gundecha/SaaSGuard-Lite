# Operational Runbook: Handling Failed Security Tests

## Objective
Provide a structured approach to investigate, mitigate, and recover from failed security tests in SaaSGuard-Lite.

---

## 1. Classify the Failure

Identify the category of failure before taking action:

### 1.1 Authentication Failure
- Invalid or expired token
- Incorrect issuer or audience
- Token signature verification failure

### 1.2 Authorization Failure
- Cross-tenant access allowed or incorrectly denied
- Role mismatch (viewer, analyst, tenant_admin)

### 1.3 Async Boundary Failure
- Worker using incorrect tenant context
- Queue payload contains unauthorized data (anything beyond job_id)

### 1.4 Data Exposure Failure
- Export contains data from multiple tenants
- Unauthorized access to CSV files in object storage

---

## 2. Investigation

### 2.1 Logs (Loki / Structured Logs)
Check logs for:
- `tenant_id`
- `job_id`
- `user_id`
- `event_name`
- `outcome`

Key questions:
- Does the requester’s tenant match the job’s tenant?
- Was the request denied or incorrectly allowed?

---

### 2.2 Database (PostgreSQL – Source of Truth)
Verify:
- `export_jobs.tenant_id`
- `memberships` for user access
- `audit_events` for activity tracking

Key questions:
- Was the job created with the correct tenant?
- Is the user actually authorized for that tenant?

---

### 2.3 Token Validation Path
Check:
- Issuer consistency
- Audience (`aud`)
- Subject mapping (`sub → users.keycloak_sub`)

---

### 2.4 Async Queue Boundary (Critical)
Verify:
- Redis payload contains only `job_id`
- Worker reloads job from PostgreSQL

Any deviation is a design-level security issue.

---

## 3. Mitigation (Immediate Containment)

### 3.1 Cross-Tenant Access Detected
- Disable affected endpoints (`GET /jobs/{job_id}`, `/download`)
- Enforce strict tenant checks in API
- Stop worker if async leakage suspected

### 3.2 Authentication Issues
- Reject all incoming requests (fail closed)
- Fix token validation configuration

### 3.3 Data Exposure (MinIO)
- Disable public access to buckets
- Rotate credentials and signed URLs

---

## 4. Root Cause Analysis

Identify the underlying issue:

Examples:
- Authorization logic relied on token roles instead of database memberships
- Worker trusted queue payload instead of database
- Missing tenant filter in database query
- Improper validation in job access endpoint

---

## 5. Recovery

Steps:
- Patch the code
- Add regression tests for the failure
- Re-run failed tests
- Validate using logs and API calls
- Reprocess affected jobs if safe
- Rotate credentials if exposure occurred

---

## 6. Preventive Actions

- Add security tests for:
  - Cross-tenant access
  - Async worker validation
- Improve logging coverage and correlation
- Add alerts for abnormal access patterns
- Consider stronger isolation (e.g., database-level controls)

---

## 7. Validation

System is considered recovered when:
- Security tests pass
- No abnormal logs are observed
- Manual verification confirms tenant isolation