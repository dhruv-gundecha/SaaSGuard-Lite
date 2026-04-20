# OE Dashboard — SaaSGuard-Lite

This system does not use a single custom dashboard container.

Instead, it uses two specialized tools:

## 1. Uptime Kuma (Availability Layer)

Purpose:
- Detects whether services are up or down
- Provides immediate visibility into system health

Monitors include:
- API (internal)
- Frontend (external)
- Keycloak
- PostgreSQL (TCP)
- Redis (TCP)
- MinIO
- Grafana
- Prometheus

Key Insight:
Uptime Kuma answers:
→ "Is the system up?"

---

## 2. Grafana (Metrics & Analysis Layer)

Purpose:
- Visualizes Prometheus metrics
- Enables root cause analysis

Dashboards include:
- API request latency
- API error rates
- authentication failures
- job processing metrics

Key Insight:
Grafana answers:
→ "Why is the system failing?"

---

## Design Rationale

Instead of combining everything into one UI, the system separates:

- Detection (Kuma)
- Diagnosis (Grafana)

This reflects real-world production systems where:
- uptime monitoring and observability are decoupled
- different tools serve different operational purposes

---

## Limitations

- No single-pane-of-glass view yet
- Requires switching between tools
- Manual correlation between uptime and metrics

This is acceptable for a prototype system.