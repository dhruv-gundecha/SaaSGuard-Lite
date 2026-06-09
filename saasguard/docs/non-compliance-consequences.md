# Non-Compliance Consequences

For SaaSGuard-Lite, non-compliance should be understood as a control failure with practical security and operational consequences, not just a paperwork gap.

## Main Consequence Areas

### 1. Cross-tenant trust failure

If authorization or worker trust boundaries fail, the result is not a small bug. It becomes a platform-boundary failure between customers.

Practical consequence:

- severe loss of confidence in tenant isolation
- incident-response burden
- likely remediation and governance scrutiny in a real environment

### 2. Authentication-path failure

If OIDC validation is weak or misconfigured, valid users may be locked out or invalid tokens may be accepted.

Practical consequence:

- service disruption
- confusing incident symptoms
- reduced confidence in identity controls

### 3. Weak auditability

If critical actions are not logged or retained well enough, security review and incident reconstruction become slow and unreliable.

Practical consequence:

- slower containment
- poor root-cause confidence
- weaker evidence for control effectiveness

### 4. Weak observability governance

If global operator tooling is broadly exposed, the observability layer itself becomes a confidentiality concern.

Practical consequence:

- operational data leakage
- broader-than-necessary access to cross-tenant context

### 5. Weak recovery posture

If queue, storage, or auth incidents can be detected but not recovered cleanly, the platform still fails availability expectations.

Practical consequence:

- prolonged outages
- repeated customer disruption
- weak confidence in operational readiness

## Why This Matters for This Repository

The repository is intentionally realistic enough that these failures are meaningful:

- it is multi-tenant
- it uses a real identity provider in local development
- it has asynchronous work and object storage
- it exposes operator dashboards and aggregated logs

That makes security, monitoring, and preparedness failures academically relevant even though the project is a mock platform.
