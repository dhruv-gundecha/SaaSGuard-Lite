# Incident Simulation

## Incident Narrative

The current simulated incident in SaaSGuard-Lite is an authentication-path regression caused by an incorrect API OIDC issuer configuration. This was chosen because it reflects a realistic failure mode in which the platform is mostly up, but valid users still cannot establish working application sessions.

## Scenario

- baseline:
  - frontend loads normally
  - valid users can authenticate
  - tenant context resolves
  - export creation and download work
  - Grafana dashboards show healthy signals
- injected fault:
  - `OIDC_ISSUER` in the API is changed from the real local Keycloak issuer to an incorrect hostname
  - the API container is recreated so the wrong issuer becomes active

Expected impact:

- the browser UI can still load
- token validation in the API fails
- users see broken identity or tenant context
- authenticated workflows stop working even though several services are still reachable

## Root Cause

The API validated access tokens against the wrong issuer value. Tokens issued by the real Keycloak realm were therefore rejected during bearer-token validation.

This walkthrough also exposed a testing gap that previously existed in the repository: many endpoint tests injected `AuthenticatedUser` directly and therefore validated authorization behavior after authentication, but not the OIDC/JWT validation path itself. Targeted deterministic tests now cover valid-token acceptance plus issuer, audience, expiration, signature, and subject failures in `tests/test_oidc_authentication.py`.

## Detection Process

1. User-visible symptoms appear first:
   - `Unknown user`
   - `No tenant scope`
   - `Invalid bearer token`
2. Uptime Kuma is checked to distinguish a broad outage from an auth-path failure.
3. Grafana is reviewed for auth-related spikes.
4. Loki is queried for token rejection events.
5. API OIDC configuration is compared with the real Keycloak realm issuer.

## Grafana Evidence

The current Grafana evidence path is:

- `Auth and Security / Token Validation Failures`
- `Auth and Security / Authorization Denials`
- `Service Health / Auth Failure Rate`

What should be visible:

- token validation failures rising
- denied activity increasing because authenticated workflows fail downstream

## Loki Evidence

The current Loki evidence path is:

- query: `{compose_service="api"} | json | event_name="auth.token_rejected"`

Expected log evidence:

- `event_name="auth.token_rejected"`
- `error_type="InvalidIssuerError"` or equivalent issuer-validation failure context

Why this matters:

- it narrows the issue to the auth-validation path instead of generic API downtime

## Uptime Kuma Evidence

Uptime Kuma is used as the first availability discriminator, not as the root-cause tool.

Expected evidence pattern:

- API may still be reachable
- Keycloak may still be reachable
- other dependencies may still be healthy

This matters because the incident is not a simple “everything is down” outage. It is a correctness failure in authentication validation.

## Recovery Process

1. Restore the correct `OIDC_ISSUER`.
2. Recreate or restart the API so the corrected value is active.
3. Re-test a valid login and authenticated API flow.

## Verification Process

Recovery is considered successful only when both product behavior and observability signals recover.

Verification checklist:

1. the frontend shows a valid user again
2. tenant context is restored
3. `/me` returns a valid session
4. `POST /exports` succeeds for a valid tenant user
5. token validation failures stop increasing
6. no new matching Loki rejections appear for the corrected scenario

## Preparedness Document Mapping

This scenario is supported by:

- architecture understanding in [architecture.md](architecture.md)
- threat modeling in [threat-model.md](threat-model.md)
- security test planning in [security_tests.md](../security_tests.md)
- runbook guidance in [incident-runbook.md](incident-runbook.md)
- OE dashboard validation in [oe-dashboard-verification.md](oe-dashboard-verification.md)
- manual drill guidance in [manual-tests-and-missing-alerts.md](manual-tests-and-missing-alerts.md)

## Compliance Relevance

This incident is relevant to the current compliance mapping because it exercises:

- authentication control correctness
- monitoring and incident detection capability
- operational response quality
- evidence collection through logs, metrics, and runbooks

It supports the current repository’s discussion of SOC 2-style Security and Availability expectations, while not claiming formal certification.

## Pareto Principle Analysis

This incident class is high value because a relatively small number of authentication-path failures can cause a large share of user-facing disruption and operator confusion.

Why it fits a Pareto-style analysis:

- one misconfigured auth setting can break many workflows
- the initial symptom can look like UI, API, or provisioning failure
- the same investigation pattern applies to several neighboring incidents

## Similar Incident Classes

The same preparedness pattern should also cover:

- audience mismatch
- JWKS endpoint failure
- stale or rotated signing-key mismatch
- expired-token rejection spikes due to refresh problems
- Keycloak outage where token issuance fails
- provisioning mismatch where the token is valid but the internal user mapping fails

## Evidence

Recording: [incident-video.mp4](../incident-video.mp4)

Video:

- `<GitHub link or local filename>`

Screenshots:

- Grafana auth failures
- Loki `InvalidIssuerError`
- Uptime Kuma healthy services
- Successful recovery
