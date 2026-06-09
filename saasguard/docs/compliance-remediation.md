# Compliance Remediation Notes

This file tracks remediation themes that remain relevant after the documentation refresh.

## Current Priority Remediations

1. Keep the GitHub Actions workflow aligned with the repository-root structure and current env templates.
2. Add one live identity-provider smoke test in CI on top of the deterministic OIDC contract-failure tests already present in `tests/test_oidc_authentication.py`.
3. Reduce frontend environment exposure to `VITE_*` values only.
4. Keep committed Grafana alert definitions and add production-grade routing plus any additional high-value signals that are still missing.
5. Replace incident-simulation placeholders with final evidence.

## Recently Strengthened Areas

- dedicated threat-model document
- security testing matrix
- clearer incident runbook structure
- improved incident-simulation documentation
- more accurate architecture and OE documentation
- CI env bootstrapping and frontend build validation in the root workflow
