# Security Test Documentation: SaaSGuard-Lite

## 1. Overview

This document defines initial security test cases for the SaaSGuard-Lite export system.

The goal is to verify:
- user identity handling
- tenant isolation
- correct async processing
- secure data storage

---

## 2. Test Environment

- Docker Compose setup
- API: http://localhost:8000
- PostgreSQL, Redis, Worker, MinIO running

---

## 3. Assumptions

- Authentication uses `X-User` header
- Users:
  - alice → tenant_alpha
  - bob → tenant_beta

---

## 4. Security Objectives

- Only valid users can create exports
- Users can only access their own jobs
- Worker must use correct tenant context
- Export data must be tenant-scoped
- Storage paths must be tenant-scoped

---

## 5. Test Cases

### 5.1 Authentication Tests

#### Test 1: Valid User

Request:
POST /exports
X-User: alice

Expected:
- Export job is created successfully

---

#### Test 2: Missing User Header

Request:
POST /exports

Expected:
- Request is rejected

---

#### Test 3: Invalid User

Request:
POST /exports
X-User: unknown

Expected:
- Request is rejected

---

### 5.2 Authorization Tests

#### Test 4: Access Own Job

- alice creates a job  
- alice requests job status  

Expected:
- Access allowed

---

#### Test 5: Cross-Tenant Job Access

- alice creates a job  
- bob requests that job  

Expected:
- Access denied

---

### 5.3 Export Data Tests

#### Test 6: Tenant Data Isolation (alice)

- alice creates export  

Expected:
- CSV contains only tenant_alpha data

---

#### Test 7: Tenant Data Isolation (bob)

- bob creates export  

Expected:
- CSV contains only tenant_beta data

---

### 5.4 Worker Processing Tests

#### Test 8: Queue Payload Validation

- Inspect queue message  

Expected:
- Only job_id is present

---

#### Test 9: Worker Uses Database Context

- Worker processes job  

Expected:
- Worker loads job from PostgreSQL  
- Uses tenant_id from job  
- Does not rely on user input  

---

### 5.5 Storage Tests

#### Test 10: Object Path Structure

Expected:
exports/&lt;tenant&gt;/&lt;job_id&gt;.csv

---

#### Test 11: Cross-Tenant File Access

- Attempt to access another tenant’s file  

Expected:
- Access is not allowed or not exposed  

---

### 5.6 Negative Tests

#### Test 12: Invalid Job ID

Request:
GET /jobs/invalid_id

Expected:
- Error response  

---

#### Test 13: Unauthorized Job Access

- User attempts to access job from another tenant  

Expected:
- Access denied  

---

## 6. Evidence Collection

- API responses  
- PostgreSQL job records  
- MinIO object paths  

---

## 7. Limitations

- Uses simple X-User header instead of real authentication  
- No audit logging  
- No rate limiting  
