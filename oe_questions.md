# Operational Excellence Questions — SaaSGuard-Lite

This system uses:
- Uptime Kuma for availability and dependency monitoring
- Grafana (Prometheus metrics) for performance and behavioral analysis

## 1. Is the system up?
(Check Uptime Kuma)

- Is the API reachable?
- Is the frontend accessible?
- Are Keycloak, Postgres, Redis, and MinIO reachable?

---

## 2. Is authentication working?
(Check Grafana)

- Are users successfully logging in?
- Are token validation failures increasing?
- Are requests being rejected due to invalid tokens?

---

## 3. Is authorization working correctly?
(Check Grafana)

- Are access-denied events increasing?
- Are users failing to access tenants unexpectedly?
- Are cross-tenant access attempts being blocked?

---

## 4. Is the async job system healthy?
(Check Grafana)

- Are jobs being completed successfully?
- Are job failures increasing?
- Are jobs getting stuck or retried repeatedly?

---

## 5. Is performance degrading?
(Check Grafana)

- Are API latencies increasing?
- Are error rates rising?
- Are specific endpoints (e.g., /jobs) slow?

---

## 6. Are dependencies healthy?
(Check Uptime Kuma)

- Is PostgreSQL reachable?
- Is Redis reachable?
- Is MinIO responding?
- Is Keycloak available?

---

## 7. Where is the problem when something breaks?
(Check both)

- Use Kuma to identify which service is down
- Use Grafana to identify why it is failing