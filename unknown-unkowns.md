# Unknown Unknowns: SaaSGuard-Lite Risk Analysis

## Objective
Identify potential risks that are not fully understood or may emerge due to system assumptions, dependencies, or scale.

---

## 1. Scale and Load Risks

### 1.1 Unexpected User Growth
- System may not handle large numbers of concurrent export requests
- Worker backlog may grow, increasing queue wait time
- Database contention may impact job creation and reads

### 1.2 Distributed Denial of Service (DDoS)
- Malicious users may flood `POST /exports`
- API and worker resources may be exhausted
- Could lead to denial of service for legitimate users

---

## 2. Async Processing Risks

- Worker retry logic may cause duplicate exports
- Race conditions in job claiming
- Queue delays causing stale or inconsistent job states
- Future changes may accidentally include sensitive data in Redis payload

---

## 3. Multi-Tenant Isolation Risks

- Missing `tenant_id` filter in a query
- Incorrect JOIN exposing cross-tenant data
- Future features bypassing authorization checks

---

## 4. Identity and Authentication Risks

- Keycloak misconfiguration (issuer, audience mismatch)
- Missing or malformed token claims
- Identity mapping (`sub`) inconsistencies

---

## 5. Object Storage Risks (MinIO)

- Predictable object keys leading to unauthorized access
- Misconfigured bucket permissions
- Reuse of presigned URLs

---

## 6. Dependency Risks

### PostgreSQL
- Partial writes or inconsistent state during failures

### Redis
- Message loss or duplication
- Out-of-order job execution

### Worker (Celery)
- Duplicate processing due to retries
- Failure to properly update job state

---

## 7. Observability Blind Spots

- Missing logs for critical actions
- Incomplete correlation between logs
- Metrics not capturing security-relevant events

---

## 8. Internal Threat Risks

- Insider misuse of privileged roles (tenant_admin)
- Unauthorized data access via direct database queries
- Misuse of development flags or elevated access

---

## 9. Configuration Risks

- Incorrect environment variables
- Inconsistent Keycloak hostname configuration
- Development settings enabled in production

---

## 10. Future Feature Risks

- Signup feature introducing incorrect user mapping
- New APIs bypassing authorization checks
- Bulk export functionality increasing data exposure risk

---

## Conclusion

These risks highlight areas where assumptions may fail. Continuous monitoring, testing, and validation are required to detect and mitigate these unknowns as the system evolves.