# CI/CD Gaps

This document reflects the current checked-in workflow state after the final CI cleanup.

## Current Workflow

Workflow file: `.github/workflows/tests.yml`

Current intended behavior:

- bootstrap backend `.env` from `.env.example`
- bootstrap `frontend/.env` from `frontend/.env.example`
- validate `docker compose config`
- boot Compose
- show running services
- run API pytest
- run frontend build
- tear down containers

## Current Gaps

- OE verification is not currently part of CI
- no live Keycloak/browser E2E auth flow is currently part of CI

## Recommended Fixes

1. optionally add OE metric verification steps
2. add one live Keycloak/browser smoke test if scope expands
