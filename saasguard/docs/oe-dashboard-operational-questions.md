# OE Dashboard Operational Questions

The current Operations page and Grafana dashboards are designed to answer these first-response questions:

1. Is the API healthy enough for users to log in and request exports?
2. Is the export pipeline moving work through the queue?
3. Is the worker failing or retrying?
4. Are auth failures rising?
5. Are authorization denials rising?
6. Is there evidence of cross-tenant probing?
7. Are PostgreSQL, Redis, MinIO, and Keycloak healthy?
8. Does the application look unstable even when dependencies are healthy?

Primary sources:

- frontend `Operations` page
- Grafana `Service Health`
- Grafana `Tenant Impact`
- Grafana `Auth and Security`
- Prometheus
- Loki
- Uptime Kuma
