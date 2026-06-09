# CI/CD Gaps

This document reflects the current checked-in workflow state.

## Current Workflow

Workflow file: `.github/workflows/tests.yml`

Current intended behavior:

- boot Compose
- show running services
- run API pytest
- tear down containers

## Current Gaps

- `working-directory: saasguard` should be verified against the real repository root
- `.env` is not created from `.env.example`
- `frontend/.env` is not created from `frontend/.env.example`
- frontend production build is not currently run in GitHub Actions
- OE verification is not currently part of CI

## Recommended Fixes

1. remove or correct the working directory setting
2. create both `.env` files from committed templates
3. add frontend build validation
4. optionally add `docker compose config` and OE metric verification steps
