import { useAuthedQuery } from "../hooks/useAuthedQuery";
import { formatDurationSeconds, formatMillis, formatPercent } from "../lib/format";
import { OperationsSummaryResponse } from "../lib/types";
import { EmptyState } from "../components/EmptyState";
import { ErrorPanel } from "../components/ErrorPanel";
import { LoadingState } from "../components/LoadingState";
import { MetricCard } from "../components/MetricCard";
import { useTenant } from "../tenant/TenantProvider";

export function HomePage() {
  const tenant = useTenant();
  const summary = useAuthedQuery<OperationsSummaryResponse>(
    tenant.activeTenantId ? "/operations/summary" : null,
    { pollMs: 15000 },
  );

  return (
    <section className="page-section">
      <div className="page-header">
        <div>
          <span className="eyebrow">Dashboard</span>
          <h2>Identity and tenant overview</h2>
        </div>
      </div>

      <div className="grid two-column">
        <div className="panel">
          <h3>Current identity</h3>
          <dl className="detail-grid">
            <div>
              <dt>Username</dt>
              <dd>{tenant.session?.user.username ?? "Unknown"}</dd>
            </div>
            <div>
              <dt>Internal user ID</dt>
              <dd>{tenant.session?.user.id ?? "Unavailable"}</dd>
            </div>
            <div>
              <dt>Active tenant</dt>
              <dd>{tenant.activeMembership?.tenant_name ?? "Select a tenant"}</dd>
            </div>
            <div>
              <dt>Role</dt>
              <dd>{tenant.activeMembership?.role ?? "Unavailable"}</dd>
            </div>
          </dl>
        </div>

        <div className="panel">
          <h3>Access model</h3>
          <ul className="plain-list">
            <li>Authentication comes from Keycloak OIDC.</li>
            <li>Tenant membership and roles come from the application.</li>
            <li>Redis is transport only. The worker reloads job context from PostgreSQL.</li>
            <li>All views in this console are scoped to the active tenant.</li>
          </ul>
        </div>
      </div>

      {!tenant.activeTenantId ? (
        <EmptyState
          title="Tenant selection required"
          description="Choose an authorized tenant in the top bar to load tenant-scoped data."
        />
      ) : summary.loading ? (
        <LoadingState label="Loading operations summary" />
      ) : summary.error ? (
        <ErrorPanel message={summary.error} />
      ) : summary.data ? (
        <div className="grid metrics-grid">
          <MetricCard label="Overall health" value={summary.data.overall_status} />
          <MetricCard
            label="API p95 latency"
            tone={summary.data.api.status === "unhealthy" ? "danger" : summary.data.api.status === "degraded" ? "neutral" : "success"}
            value={formatMillis(summary.data.api.p95_latency_ms)}
          />
          <MetricCard
            label="Completed (1h)"
            tone="success"
            value={summary.data.exports.completed_last_hour}
          />
          <MetricCard
            label="API 5xx rate"
            tone={summary.data.api.error_rate > 0.02 ? "danger" : "neutral"}
            value={formatPercent(summary.data.api.error_rate)}
          />
          <MetricCard
            label="Backlog"
            tone={summary.data.exports.status === "unhealthy" ? "danger" : "neutral"}
            value={summary.data.exports.queued + summary.data.exports.retry_pending}
          />
          <MetricCard
            label="Oldest pending job"
            value={formatDurationSeconds(summary.data.exports.oldest_pending_age_seconds)}
          />
        </div>
      ) : null}
    </section>
  );
}
