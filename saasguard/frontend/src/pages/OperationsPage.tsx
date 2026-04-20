import { MetricCard } from "../components/MetricCard";
import { EmptyState } from "../components/EmptyState";
import { ErrorPanel } from "../components/ErrorPanel";
import { LoadingState } from "../components/LoadingState";
import { useAuthedQuery } from "../hooks/useAuthedQuery";
import { formatRelativeMinutes } from "../lib/format";
import { env } from "../lib/env";
import { OperationsSummaryResponse } from "../lib/types";
import { useTenant } from "../tenant/TenantProvider";

const dashboards = [
  { label: "Service Health", href: `${env.grafanaUrl}/d/saasguard-service-health` },
  { label: "Tenant Impact", href: `${env.grafanaUrl}/d/saasguard-tenant-impact` },
  { label: "Auth and Security", href: `${env.grafanaUrl}/d/saasguard-auth-security` },
];

export function OperationsPage() {
  const tenant = useTenant();
  const summary = useAuthedQuery<OperationsSummaryResponse>(
    tenant.activeTenantId ? "/operations/summary" : null,
    { pollMs: 15000 },
  );

  return (
    <section className="page-section">
      <div className="page-header">
        <div>
          <span className="eyebrow">Operations</span>
          <h2>Operational excellence workspace</h2>
          <p className="muted">Use this page to pivot into dashboards, logs, and tenant-specific failure context during demos or incidents.</p>
        </div>
      </div>

      {!tenant.activeTenantId ? (
        <EmptyState title="No tenant selected" description="Choose a tenant to load the local operations summary." />
      ) : summary.loading ? (
        <LoadingState label="Loading operations summary" />
      ) : summary.error ? (
        <ErrorPanel message={summary.error} />
      ) : summary.data ? (
        <>
          <div className="grid metrics-grid">
            <MetricCard label="Tenant queued jobs" value={summary.data.summary.queued_jobs} />
            <MetricCard
              label="Tenant failed jobs"
              tone={summary.data.summary.failed_jobs > 0 ? "danger" : "neutral"}
              value={summary.data.summary.failed_jobs}
            />
            <MetricCard
              label="Auth denials (24h)"
              tone={summary.data.summary.authorization_denials_last_24h > 0 ? "danger" : "neutral"}
              value={summary.data.summary.authorization_denials_last_24h}
            />
            <MetricCard
              label="Upload failures (24h)"
              tone={summary.data.summary.upload_failures_last_24h > 0 ? "danger" : "neutral"}
              value={summary.data.summary.upload_failures_last_24h}
            />
            <MetricCard
              label="Global backlog"
              value={summary.data.global_queue.queued_jobs}
            />
            <MetricCard
              label="Oldest pending"
              value={formatRelativeMinutes(summary.data.global_queue.oldest_pending_job_age_seconds / 60)}
            />
          </div>

          <div className="grid two-column">
            <div className="panel">
              <h3>Dashboards</h3>
              <ul className="link-list">
                {dashboards.map((dashboard) => (
                  <li key={dashboard.label}>
                    <a href={dashboard.href} rel="noreferrer" target="_blank">
                      {dashboard.label}
                    </a>
                  </li>
                ))}
                <li>
                  <a href={summary.data.links.prometheus} rel="noreferrer" target="_blank">
                    Prometheus targets and ad hoc queries
                  </a>
                </li>
                <li>
                  <a href={summary.data.links.minio_console} rel="noreferrer" target="_blank">
                    MinIO console for object inspection
                  </a>
                </li>
              </ul>
            </div>

            <div className="panel">
              <h3>Loki quick-start</h3>
              <p>Grafana handles most log review, but these filters are useful during local failure simulations:</p>
              <code className="query-block">{`{compose_service="api"} | json | event_name="auth.token_rejected"`}</code>
              <code className="query-block">{`{compose_service="worker"} | json | tenant_id="${tenant.activeTenantId}"`}</code>
            </div>
          </div>
        </>
      ) : null}
    </section>
  );
}
