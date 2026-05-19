import { useAuthedQuery } from "../hooks/useAuthedQuery";
import { DashboardSummaryResponse } from "../lib/types";
import { EmptyState } from "../components/EmptyState";
import { ErrorPanel } from "../components/ErrorPanel";
import { LoadingState } from "../components/LoadingState";
import { MetricCard } from "../components/MetricCard";
import { useTenant } from "../tenant/TenantProvider";

export function HomePage() {
  const tenant = useTenant();
  const hasTenantScope = Boolean(tenant.activeMembership?.tenant_id);
  const summary = useAuthedQuery<DashboardSummaryResponse>(
    hasTenantScope ? "/dashboard/summary" : null,
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
            <li>Global operations access is reserved for internal SOC or operator users.</li>
            <li>Redis is transport only. The worker reloads job context from PostgreSQL.</li>
            <li>Tenant users receive tenant-scoped views instead of raw global observability links.</li>
          </ul>
        </div>
      </div>

      {!hasTenantScope ? (
        <EmptyState
          title={
            tenant.session?.authorization.can_access_operations
              ? "Internal operations session"
              : "Tenant selection required"
          }
          description={
            tenant.session?.authorization.can_access_operations
              ? "This account can access the global Operations page. Tenant-scoped dashboard cards are only available when the session has an active tenant membership."
              : "Choose an authorized tenant in the top bar to load tenant-scoped data."
          }
        />
      ) : summary.loading ? (
        <LoadingState label="Loading tenant summary" />
      ) : summary.error ? (
        <ErrorPanel message={summary.error} />
      ) : summary.data ? (
        <div className="grid metrics-grid">
          <MetricCard label="Tenant queued jobs" value={summary.data.summary.queued_jobs} />
          <MetricCard
            label="Tenant failed jobs"
            tone={summary.data.summary.failed_jobs > 0 ? "danger" : "success"}
            value={summary.data.summary.failed_jobs}
          />
          <MetricCard
            label="Completed (24h)"
            tone="success"
            value={summary.data.summary.completed_jobs_last_24h}
          />
          <MetricCard
            label="Upload failures (24h)"
            tone={summary.data.summary.upload_failures_last_24h > 0 ? "danger" : "neutral"}
            value={summary.data.summary.upload_failures_last_24h}
          />
          <MetricCard
            label="Auth denials (24h)"
            tone={summary.data.summary.authorization_denials_last_24h > 0 ? "neutral" : "success"}
            value={summary.data.summary.authorization_denials_last_24h}
          />
        </div>
      ) : null}
    </section>
  );
}
