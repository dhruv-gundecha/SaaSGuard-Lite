# Oncall Analysis — SaaSGuard-Lite

## Key Principle

The oncall uses:
- Uptime Kuma to detect failures
- Grafana to diagnose root cause

---

## Scenario 1: API Down

Step 1: Check Kuma
- API monitor down → confirm issue

Step 2: Check dependencies
- If Postgres or Redis down → root cause found
- If all dependencies up → API issue

Step 3: Confirm in Grafana
- Requests drop to zero

---

## Scenario 2: Users Cannot Login

Step 1: Check Kuma
- Keycloak up or down?

Step 2: Check Grafana
- spike in auth failures
- token validation errors

Conclusion:
- Keycloak down → dependency failure
- Keycloak up + failures → configuration issue

---

## Scenario 3: Jobs Not Processing

Step 1: Check Grafana
- job failures increasing?
- job completion dropping?

Step 2: Check Kuma
- Redis down → queue issue
- MinIO down → storage failure

---

## Scenario 4: Performance Degradation

Step 1: Check Grafana
- latency increase
- error rate increase

Step 2: Identify endpoint (/jobs)

Step 3: Correlate with:
- DB usage
- job load

---

## Scenario 5: Partial System Failure

Step 1: Check Kuma
- identify which services are down

Step 2: Use Grafana
- identify impact on traffic and errors

---

## Final Insight

The system is designed so that:

- Kuma answers:
  → "What is broken?"

- Grafana answers:
  → "Why is it broken?"

This separation enables faster and clearer incident response.