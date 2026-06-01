# Incident Summary

Name: Authentication Configuration Regression

# Objective

The goal of this simulation was to test whether the SaaSGuard-Lite incident runbook helps an operator detect, investigate, and recover from a realistic authentication failure without assuming a full platform outage. The recorded incident focused on a configuration regression in the API's OIDC validation path.

# Baseline

Before the fault was introduced:

- the UI loaded normally
- authenticated users had visible identity information
- tenant context was present
- export creation and download worked
- Grafana dashboards were healthy

# Fault Injection

The simulated incident changed the API OIDC issuer configuration from:

```text
OIDC_ISSUER=http://auth.saasguard.local:8081/realms/saasguard
```

to:

```text
OIDC_ISSUER=http://wrong-host:8081/realms/saasguard
```

After the configuration change, the API container was recreated so the incorrect issuer value became active in the running service.

# Detection

The first customer-visible symptom was that the frontend still loaded, but authenticated state was broken. Users saw:

- `Unknown user`
- `No tenant scope`
- `Invalid bearer token`

Observability signals confirmed the pattern was not a generic outage:

- Grafana `Auth and Security` showed `Token Validation Failures` increasing
- Grafana also showed `Denied Event Volume` increasing
- Loki showed `event_name="auth.token_rejected"`
- Loki error details included `error_type="InvalidIssuerError"`

# Investigation

The investigation followed the runbook flow for token validation failures:

1. Uptime Kuma was checked first.
2. Uptime Kuma showed core services such as API, Keycloak, PostgreSQL, Redis, and worker were still up.
3. Because services were available, the incident was treated as an authentication-path failure rather than a full service outage.
4. Loki was reviewed for `auth.token_rejected` events.
5. The `error_type` values were inspected and showed `InvalidIssuerError`.
6. The API OIDC configuration was compared against the expected Keycloak issuer.
7. The configured API issuer did not match the actual Keycloak realm issuer.
8. The root cause was identified as configuration drift between the API OIDC issuer configuration and the real Keycloak issuer.

This step mattered because `InvalidIssuerError` alone does not prove configuration drift. Similar symptoms could also come from malicious tokens, expired tokens, or frontend token handling issues. The configuration comparison was the point where the root cause became specific.

# Response

Response actions were limited to correcting the regression and reloading the affected service:

1. Restore the correct `OIDC_ISSUER` value.
2. Recreate the API container.
3. Re-test authenticated requests and UI state.

# Recovery Validation

After the API was recreated with the correct issuer:

- the UI again showed valid user identity
- tenant context was restored
- valid API requests worked again
- export creation worked
- token validation failures stopped increasing
- no new matching Loki `auth.token_rejected` events appeared after recovery for the same condition

Recovery validation focused on both user-facing behavior and observability. Service uptime alone would not have been sufficient because the main failure mode was incorrect token validation in an otherwise running stack.

# Evidence Collected

The recorded evidence set for this incident included:

- UI failure state showing broken user and tenant context
- Grafana token validation spike
- Loki `InvalidIssuerError` logs
- OIDC configuration check
- recovery state after restoring the correct issuer
