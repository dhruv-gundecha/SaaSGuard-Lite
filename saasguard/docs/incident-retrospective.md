# Incident Retrospective Notes

The current simulated OIDC issuer mismatch incident remains a good preparedness scenario because it separates authentication correctness from generic service uptime.

## What Worked

- Grafana showed auth-failure trends
- Loki narrowed investigation with token-rejection evidence
- Uptime Kuma helped rule out a full outage
- the runbook correctly emphasizes that the Operations page may be unavailable during auth-wide failures

## What Still Needs Improvement

- keep the new deterministic OIDC contract-failure tests in CI and add one live Keycloak smoke test later
- attach final screenshots or recording evidence
- verify the CI workflow against the real repository root
