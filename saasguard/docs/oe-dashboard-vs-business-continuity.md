# OE Dashboard vs Business Continuity

This document compares the original business-risk analysis with what the current Operations Overview dashboard can actually detect or answer today.

## Tenant Data Exposure

- **Business impact:** legal exposure, severe trust loss, and incident-response obligations if one tenant can access another tenant’s data.
- **Current OE coverage:** partial. The Operations page shows authorization denials and cross-tenant denial counts and routes operators into auth and log investigation quickly.
- **Remaining gap:** the dashboard can detect denied attempts, but it cannot prove the absence of a successful exposure. Automated isolation tests and code review still do the heavier lifting.
- **Future improvement:** add explicit alerting on cross-tenant denial spikes and correlate them with audit-event patterns in Grafana/Loki.

## Export Misconfiguration or Pipeline Failure

- **Business impact:** customers request exports but never receive them, which makes the core product appear broken.
- **Current OE coverage:** strong. The Operations page summarizes queue depth, retry-pending work, processing jobs, completed-last-hour, failed-last-hour, oldest pending age, and worker instability.
- **Remaining gap:** the current view is more global than tenant-cohort specific. It does not yet explain whether a failure wave began after a deployment, a data anomaly, or a dependency outage without operator follow-up.
- **Future improvement:** add release markers and more explicit per-stage export failure trends.

## Queue Backlog or Worker Instability

- **Business impact:** delayed or failed exports create usability degradation and support load, even if authentication still works.
- **Current OE coverage:** strong. Queue pressure and worker retry/failure indicators are first-class on the product page and in Grafana.
- **Remaining gap:** there is no dedicated worker heartbeat or “no completions in recent window” product signal yet.
- **Future improvement:** add a no-completions alert and a worker-last-successful-run signal.

## High Latency

- **Business impact:** customers experience slow job creation, slow job inspection, or general product frustration before a hard outage occurs.
- **Current OE coverage:** moderate to strong. API request rate, API 5xx rate, and p95 latency are summarized directly in the product and linked to Grafana.
- **Remaining gap:** no frontend latency telemetry, no p99 summary in the product page, and no explicit latency-based alert rules committed in this repo yet.
- **Future improvement:** add frontend performance signals and promote p95/p99 thresholds into alerting rules.

## Outage

- **Business impact:** customers cannot log in, create exports, inspect jobs, or download finished CSVs.
- **Current OE coverage:** strong for API and dependency-aware diagnosis. The Operations page combines API health, dependency checks, and investigation links; Uptime Kuma handles uptime visibility.
- **Remaining gap:** the Operations page is not itself a replacement for edge uptime monitoring. It is strongest after the user can still reach the product or the API is at least partially alive.
- **Future improvement:** include a clearer frontend-availability summary sourced from Uptime Kuma or a lightweight status feed.

## Release Regression

- **Business impact:** a bad deploy can trigger sudden outages, latency spikes, auth failures, or export instability with no infrastructure change.
- **Current OE coverage:** moderate. The deployment indicator now highlights cases where app behavior degrades while dependencies still look healthy.
- **Remaining gap:** the signal is heuristic and not tied to actual release metadata, commit SHA, or deployment timestamp.
- **Future improvement:** add explicit deployment metadata and annotate Grafana dashboards with release events.

## Dependency Failure

- **Business impact:** PostgreSQL, Redis, MinIO, or Keycloak outages break critical parts of the login, authorization, queue, or export path.
- **Current OE coverage:** strong for current-state diagnosis. The Operations page performs bounded health checks and links directly to Uptime Kuma and deeper tools.
- **Remaining gap:** point-in-time checks do not replace historical uptime trends or flapping analysis.
- **Future improvement:** surface recent dependency failure history or a short rolling status timeline in the product page.

## Weak Observability

- **Business impact:** slower triage, longer outages, and weaker confidence during security-relevant incidents.
- **Current OE coverage:** improved materially. The product now acts as an operational command center with direct connections to business-impact questions and investigation tools.
- **Remaining gap:** it still depends on external observability systems for deep investigation, and some high-value alert rules remain documented rather than automated.
- **Future improvement:** add stronger alerting, deployment markers, worker heartbeat signals, and richer incident context on the Operations page without turning it into a second observability stack.
