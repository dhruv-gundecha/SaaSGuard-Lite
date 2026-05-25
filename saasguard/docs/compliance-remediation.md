# Compliance Remediation

## 1. Privileged Operations Overview Access

- Finding: Global operational visibility is sensitive because it can expose cross-tenant metrics, logs, and dependency context.
- Implemented remediation: `/operations/summary` remains backend-restricted to internal `soc_admin` and `ops_admin` roles, and successful privileged access is now audited in addition to denied access attempts.
- Evidence:
  - `src/authz.py`
  - `src/api.py`
  - `tests/test_operations_summary.py`
- Compliance mapping:
  - SOC 2 Security: logical access restrictions for sensitive operational surfaces
  - CIS Control 6: access control management
  - OWASP ASVS / OWASP Top 10 A01: server-side authorization enforcement

## 2. Explicit Tenant-Scoped Authorization Denial Evidence

- Finding: Tenant-scoped 403 paths should create standardized audit evidence instead of relying only on mixed action-specific denial records.
- Implemented remediation: Added explicit `authorization.denied` audit events and tenant-scoped denial metrics for role denials, invalid tenant selection, and cross-tenant job/download denials.
- Evidence:
  - `src/authz.py`
  - `src/api.py`
  - `src/metrics.py`
  - `tests/test_exports.py`
- Compliance mapping:
  - SOC 2 Security and Confidentiality: unauthorized access attempts must be detectable and attributable
  - CIS Control 8: audit log management
  - OWASP Top 10 A09: logging and monitoring of security-relevant failures

## 3. Security Response Headers

- Finding: The API did not consistently add defensive response headers to reduce browser-side exposure from embedding, sniffing, and cache persistence.
- Implemented remediation: Added middleware headers including `Cache-Control: no-store`, `Pragma: no-cache`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Permissions-Policy`, and a restrictive `Content-Security-Policy`.
- Evidence:
  - `src/api.py`
  - `tests/test_operations_summary.py`
- Compliance mapping:
  - SOC 2 Security: secure system operations and reduction of avoidable client-side exposure
  - OWASP ASVS: secure headers and browser handling controls

## 4. Export Request Rate Limiting

- Finding: Export creation was vulnerable to repeated request bursts that could degrade availability and increase abuse impact.
- Implemented remediation: Added a simple in-memory rate limiter for `POST /exports` keyed by user and tenant, with `429 Too Many Requests` responses and corresponding audit evidence.
- Evidence:
  - `src/rate_limit.py`
  - `src/api.py`
  - `src/config.py`
  - `tests/test_exports.py`
- Compliance mapping:
  - SOC 2 Availability: resilience against request bursts affecting service availability
  - CIS Controls: protection against service abuse and operational degradation
  - OWASP ASVS: abuse resistance and transaction protection

## Remaining Findings Not Addressed Here

- MFA enforcement is still not demonstrated in the checked-in Keycloak realm.
- Backup and recovery remain undocumented and unverified as implemented controls.
- Log retention policy is still not documented or configured as a formal control.
- Secrets handling remains local-demo oriented rather than production-compliant.
- Database least-privilege role separation is still not demonstrated.
