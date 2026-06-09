# Manual Tests and Missing Alerts

This document tracks validation that still depends on manual execution and alerting gaps that are not yet fully represented in committed workflow or alert-rule artifacts.

## Manual Tests Not Fully Automated

### Browser login through Keycloak PKCE

- Why it matters: validates the real browser auth path
- Current repo coverage: backend auth logic exists and frontend uses Keycloak PKCE
- Gap: no browser automation in CI

### Multi-tenant switching for `carol`

- Why it matters: validates `X-Active-Tenant` behavior through the real UI
- Current repo coverage: backend tenant resolution exists; session-scoped tenant switching exists in `TenantProvider`
- Gap: no E2E UI test

### UI export download

- Why it matters: validates the full user-facing report-delivery path
- Current repo coverage: backend download authorization is tested
- Gap: no browser download automation

### Uptime Kuma outage verification

- Why it matters: Uptime Kuma is part of the operational story but not fully exported as config
- Current repo coverage: service exists in Compose
- Gap: monitor definitions are not committed as a reproducible artifact

### MinIO outage and recovery drill

- Why it matters: upload-stage failure is a customer-visible reliability issue
- Current repo coverage: worker upload failure behavior is tested, dashboards include MinIO failure signals
- Gap: no recurring automated outage drill

## Alerting Gaps

Fixed since earlier audit:

- the repository now commits Grafana alert-rule definitions in `observability/grafana/provisioning/alerting/`
- committed local-demo alert coverage now includes:
  - token validation failure spike
  - authorization denial spike
  - export failure spike
  - queue backlog threshold
  - oldest pending job age threshold
  - worker failure and retry spike
  - MinIO upload failure spike

Still weak as committed automation:

- alert routing still uses a placeholder local-demo contact point rather than real destination integrations
- no completed jobs while exports continue to be requested is still not represented as a dedicated committed alert
- Uptime Kuma monitor definitions are still not exported as a reproducible repo artifact

## Current State Summary

Implemented as data sources and dashboards:

- Prometheus metrics
- Loki log queries
- Grafana dashboards
- Uptime Kuma service presence

Still weak as committed automation:

- browser incident drills
- production-grade alert routing destinations
- reproducible Uptime Kuma monitor export
