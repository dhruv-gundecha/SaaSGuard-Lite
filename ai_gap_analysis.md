# AI Gap Analysis and Improvements

## Overview

This document analyzes the differences between AI-generated suggestions and the final implementation.

---

## AI Output Observations

The AI suggested a design that focused on demonstrating security failures, especially in asynchronous processing.

It also suggested adding multiple components such as full authentication systems and observability tools.

---

## Gaps in AI Approach

### 1. Focus on Intentional Vulnerabilities

The AI initially suggested designing the system to include vulnerabilities.

This does not match the requirement to build a normal system and then analyze risks.

---

### 2. Overly Broad Design

The AI suggested:

- Keycloak for authentication
- Monitoring systems
- Additional services

These were not required for a minimal working system.

---

## What Was Kept

The following ideas were useful:

- Async processing is a risk area
- Tenant isolation is critical
- Worker must not trust queue input
- Database should be source of truth

---

## Implementation Observations

The Docker-based system worked as expected.

One issue occurred where `.env` was not correctly named and containers failed to start.

After fixing this, the system ran properly.

---

## Security Strengths

- Job state stored in PostgreSQL
- Only `job_id` passed through queue
- Worker reloads trusted job data
- Tenant-based filtering in queries
- Tenant-based object storage paths

---

## Remaining Gaps

- Weak authentication using `X-User`
- No audit logging
- No rate limiting
- Limited authorization checks on job access
- No secure access control for MinIO

---

## Improvements

- Replace `X-User` with JWT or OIDC
- Add logging for all actions
- Add rate limiting
- Enforce tenant checks on all endpoints
- Use signed URLs for file access

---

## Summary

The final system is a minimal and functional design that avoids intentional vulnerabilities and allows realistic security analysis.