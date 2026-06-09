# Security Testing Matrix

This matrix reflects the current implementation. It distinguishes between automated coverage that exists today, manual validation that is documented, and gaps that still remain.

| Requirement | Risk addressed | Automated tests | Manual tests | Current coverage | Coverage gaps | Future improvements |
| --- | --- | --- | --- | --- | --- | --- |
| Tenant isolation for job reads | cross-tenant data exposure | `tests/test_exports.py::test_get_job_denies_cross_tenant_access` | inspect job detail and tenant switching in UI | Strong backend coverage | No browser end-to-end tenant-isolation regression | Add Playwright job-read isolation flow |
| Tenant isolation for export downloads | cross-tenant data exposure through artifact retrieval | `tests/test_exports.py::test_cross_tenant_download_is_denied`, `test_completed_job_can_be_downloaded_by_same_tenant_authorized_user` | download CSV through UI as `alice` and confirm content | Strong backend coverage | No browser download automation | Add Playwright download validation |
| Authorization on export creation | unauthorized job creation | `tests/test_exports.py::test_post_exports_creates_job_for_authorized_analyst_and_enqueues_only_job_id`, `test_post_exports_rate_limits_excessive_requests` | create exports as seeded users with different roles | Good backend coverage | Missing explicit lower-role negative test in current suite | Add viewer-denied export creation test |
| Authorization on operations dashboard | exposure of global observability data to tenant users | `tests/test_operations_summary.py::test_operations_summary_denies_analyst_user`, `test_operations_summary_denies_viewer_user`, `test_operations_summary_denies_tenant_admin_user`, `test_operations_summary_allows_soc_admin_user`, `test_operations_summary_allows_ops_admin_user` | log in as `soc` and as tenant users, verify nav and route behavior | Strong backend/API coverage | No browser route-guard automation | Add frontend E2E operations-access regression |
| OIDC authentication with valid token | unauthorized API use | `tests/test_oidc_authentication.py::test_valid_jwt_is_accepted` | login through Keycloak and call `/me` and `/exports` | Good deterministic backend coverage | No explicit live Keycloak integration test in CI | Add compose integration test using real token acquisition |
| Missing bearer token rejection | unauthenticated API access | `tests/test_operational_risks.py::test_missing_bearer_token_increments_auth_failure_metric` | call `/me` without token | Strong | None for this path | Keep existing test |
| Invalid bearer token rejection | malformed or bad-signature token acceptance | `tests/test_oidc_authentication.py::test_invalid_signature_token_is_rejected`, `test_missing_subject_token_is_rejected` | invalid bearer request against `/me` and Grafana/Loki drill | Good backend coverage | No automated malformed non-JWT token case | Add explicit malformed-token test if parser regressions are a concern |
| Issuer mismatch handling | accepting tokens from wrong issuer or blocking all valid users due to config drift | `tests/test_oidc_authentication.py::test_wrong_issuer_token_is_rejected`, `test_oidc_issuer_contract_detects_discovery_mismatch` | simulated incident in `docs/incident-simulation.md` | Good automated negative coverage | No live discovery/JWKS integration test against a running IdP in CI | Add compose integration test that exercises discovery plus real token acquisition |
| Audience mismatch handling | accepting tokens for wrong audience | `tests/test_oidc_authentication.py::test_wrong_audience_token_is_rejected` | review OIDC configuration and negative-token drill | Implemented for backend token validation | No live IdP-backed integration test in CI | Keep deterministic unit test and add live compose auth smoke test later |
| Expired token rejection | stale session acceptance | `tests/test_oidc_authentication.py::test_expired_token_is_rejected` | manual expired-token negative drill | Implemented for backend token validation | No live refresh/session-expiry browser test | Add browser/session-expiry coverage later |
| Keycloak dependency failure handling | auth-path outage and degraded operations access | none in pytest | Uptime Kuma and runbook-driven manual drill | Manual only | No automated compose failure scenario | Add scheduled Keycloak outage drill |
| Queue tampering resistance | worker trusting untrusted queue payload data | `tests/test_exports.py::test_post_exports_creates_job_for_authorized_analyst_and_enqueues_only_job_id`, `test_worker_reloads_authoritative_job_context_from_database` | code review of queue payload and worker behavior | Strong design-level and unit-level coverage | No hostile integration test against broker contents | Add integration test that proves extra queue fields are ignored |
| Worker upload-failure handling | silent export loss or missing failure evidence | `tests/test_operational_risks.py::test_worker_upload_failure_marks_job_failed_and_records_metrics` | MinIO outage drill in OE verification docs | Good backend coverage | No scheduled full-stack chaos drill | Add compose-level outage scenario |
| Queue backlog visibility | customer-visible delay without clear operational signal | `tests/test_operations_summary.py::test_build_operations_summary_calculates_queue_backlog_and_failed_export_signals`, `tests/test_operational_risks.py::test_metrics_endpoint_emits_oe_dashboard_metrics` | inspect Grafana `Tenant Impact` and Operations page | Good summary/metric coverage | No alert-routing automation | Add alert validation and drift checks |
| Logging and observability safety | missing evidence or sensitive leakage | `tests/test_operations_summary.py::test_build_operations_summary_avoids_secret_values` | review logs in Loki during auth and worker failures | Partial | No broad automated structured-log schema test | Add logging contract tests |
| Security headers on API responses | weak browser-facing response hardening | `tests/test_operations_summary.py::test_security_headers_are_added_to_api_responses` | inspect `/health` response headers | Strong | None for current implementation | Keep existing test |
| Tenant-scoped dashboard summary | leaking global context to tenant users | `tests/test_operations_summary.py::test_dashboard_summary_remains_tenant_scoped_for_tenant_admin` | inspect dashboard as `carol` across tenants | Good | No browser automation | Add dashboard scope E2E test |

## Manual Test Set Still Required

- browser login through Keycloak PKCE
- tenant switching as `carol`
- export download through the UI
- Uptime Kuma outage-state validation
- live MinIO outage and recovery drill
- dashboard usefulness checks during real incidents

Current source: [docs/manual-tests-and-missing-alerts.md](/home/darthdg/saasguard/docs/manual-tests-and-missing-alerts.md)

## Highest-Priority Next Tests

1. JWKS / Keycloak drift or availability failure
2. browser-based PKCE and CSV download regression
3. malformed non-JWT bearer token rejection
4. live Keycloak token-acquisition smoke test in CI
5. browser session-expiry regression
