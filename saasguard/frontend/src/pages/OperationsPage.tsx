import { EmptyState } from "../components/EmptyState";
import { ErrorPanel } from "../components/ErrorPanel";
import { LoadingState } from "../components/LoadingState";
import { StatusBadge } from "../components/StatusBadge";
import { useAuthedQuery } from "../hooks/useAuthedQuery";
import {
  formatDecimal,
  formatDurationSeconds,
  formatMillis,
  formatPercent,
} from "../lib/format";
import { OperationsSummaryResponse } from "../lib/types";
import { useTenant } from "../tenant/TenantProvider";

function OperationsPageHeader() {
  return (
    <div className="page-header">
      <div>
        <span className="eyebrow">Operations</span>
        <h2>Operations overview command center</h2>
        <p className="muted">
          This page summarizes live product state and routes operators into the
          right investigation tool before incidents turn into customer-visible
          failures.
        </p>
      </div>
    </div>
  );
}

export function OperationsPage() {
  const tenant = useTenant();
  const summary = useAuthedQuery<OperationsSummaryResponse>(
    tenant.activeTenantId ? "/operations/summary" : null,
    { pollMs: 15000 },
  );

  if (!tenant.activeTenantId) {
    return (
      <section className="page-section">
        <OperationsPageHeader />
        <EmptyState
          title="No tenant selected"
          description="Choose a tenant to load the live operations summary."
        />
      </section>
    );
  }

  if (summary.loading) {
    return (
      <section className="page-section">
        <OperationsPageHeader />
        <LoadingState label="Loading operations summary" />
      </section>
    );
  }

  if (summary.error) {
    return (
      <section className="page-section">
        <OperationsPageHeader />
        <ErrorPanel message={summary.error} />
      </section>
    );
  }

  if (!summary.data) {
    return null;
  }

  const data = summary.data;

  return (
    <section className="page-section">
      <OperationsPageHeader />

      <div className="panel panel-accent operations-hero">
        <div>
          <span className="eyebrow">Overall health</span>
          <h3>Tenant isolation and export reliability first</h3>
          <p className="muted">
            Active tenant: {data.scope.tenant_name} ({data.scope.role}). Last
            refresh: {new Date(data.generated_at).toLocaleTimeString()}.
          </p>
        </div>
        <div className="operations-hero-status">
          <StatusBadge status={data.overall_status} />
          <p>{data.deployment.impact}</p>
        </div>
      </div>

      <div className="grid operations-grid">
        <div className="panel operations-panel">
          <div className="panel-header-inline">
            <h3>API health</h3>
            <StatusBadge status={data.api.status} />
          </div>
          <dl className="detail-grid">
            <div>
              <dt>Request rate</dt>
              <dd>{formatDecimal(data.api.request_rate)} req/min</dd>
            </div>
            <div>
              <dt>5xx rate</dt>
              <dd>{formatPercent(data.api.error_rate)}</dd>
            </div>
            <div>
              <dt>P95 latency</dt>
              <dd>{formatMillis(data.api.p95_latency_ms)}</dd>
            </div>
            <div>
              <dt>Window</dt>
              <dd>{data.api.window_minutes} minutes</dd>
            </div>
          </dl>
          <p className="muted">{data.api.impact}</p>
          <a href={data.links.grafana_service_health} rel="noreferrer" target="_blank">
            Investigate in Grafana Service Health
          </a>
        </div>

        <div className="panel operations-panel">
          <div className="panel-header-inline">
            <h3>Export pipeline</h3>
            <StatusBadge status={data.exports.status} />
          </div>
          <dl className="detail-grid">
            <div>
              <dt>Queued</dt>
              <dd>{data.exports.queued}</dd>
            </div>
            <div>
              <dt>Retry pending</dt>
              <dd>{data.exports.retry_pending}</dd>
            </div>
            <div>
              <dt>Processing</dt>
              <dd>{data.exports.processing}</dd>
            </div>
            <div>
              <dt>Completed (1h)</dt>
              <dd>{data.exports.completed_last_hour}</dd>
            </div>
            <div>
              <dt>Failed (1h)</dt>
              <dd>{data.exports.failed_last_hour}</dd>
            </div>
            <div>
              <dt>Oldest pending</dt>
              <dd>{formatDurationSeconds(data.exports.oldest_pending_age_seconds)}</dd>
            </div>
          </dl>
          <p className="muted">{data.exports.impact}</p>
          <a href={data.links.grafana_tenant_impact} rel="noreferrer" target="_blank">
            Investigate in Grafana Tenant Impact
          </a>
        </div>

        <div className="panel operations-panel">
          <div className="panel-header-inline">
            <h3>Worker health</h3>
            <StatusBadge status={data.worker.status} />
          </div>
          <dl className="detail-grid">
            <div>
              <dt>Jobs started</dt>
              <dd>{data.worker.jobs_started}</dd>
            </div>
            <div>
              <dt>Jobs completed</dt>
              <dd>{data.worker.jobs_completed}</dd>
            </div>
            <div>
              <dt>Jobs failed</dt>
              <dd>{data.worker.jobs_failed}</dd>
            </div>
            <div>
              <dt>Retries</dt>
              <dd>{data.worker.retry_count}</dd>
            </div>
            <div>
              <dt>MinIO upload failures</dt>
              <dd>{data.worker.minio_upload_failures}</dd>
            </div>
            <div>
              <dt>DB query failures</dt>
              <dd>{data.worker.db_query_failures}</dd>
            </div>
          </dl>
          <p className="muted">{data.worker.impact}</p>
          <a href={data.links.grafana_tenant_impact} rel="noreferrer" target="_blank">
            Investigate worker and export trends
          </a>
        </div>

        <div className="panel operations-panel">
          <div className="panel-header-inline">
            <h3>Security and authz</h3>
            <StatusBadge status={data.security.status} />
          </div>
          <dl className="detail-grid">
            <div>
              <dt>Auth failures</dt>
              <dd>{data.security.auth_failures}</dd>
            </div>
            <div>
              <dt>Authorization denials</dt>
              <dd>{data.security.authorization_denials}</dd>
            </div>
            <div>
              <dt>Cross-tenant denials</dt>
              <dd>{data.security.cross_tenant_denials}</dd>
            </div>
          </dl>
          <p className="muted">{data.security.impact}</p>
          <a href={data.links.grafana_auth_security} rel="noreferrer" target="_blank">
            Investigate in Grafana Auth and Security
          </a>
        </div>

        <div className="panel operations-panel">
          <div className="panel-header-inline">
            <h3>Dependencies</h3>
            <StatusBadge status={data.dependencies.status} />
          </div>
          <div className="dependency-grid">
            {(["postgres", "redis", "minio", "keycloak"] as const).map((dependency) => (
              <div className="dependency-card" key={dependency}>
                <div className="panel-header-inline">
                  <strong>{dependency}</strong>
                  <StatusBadge status={data.dependencies[dependency].status} />
                </div>
                <span>{formatMillis(data.dependencies[dependency].latency_ms)}</span>
                <small>{data.dependencies[dependency].reason}</small>
              </div>
            ))}
          </div>
          <a href={data.links.uptime_kuma} rel="noreferrer" target="_blank">
            Investigate dependency uptime in Uptime Kuma
          </a>
        </div>

        <div className="panel operations-panel">
          <div className="panel-header-inline">
            <h3>Release and deployment indicators</h3>
            <StatusBadge status={data.deployment.status} />
          </div>
          <p className="muted">{data.deployment.impact}</p>
          <ul className="plain-list">
            <li>Suspected regression: {data.deployment.suspected_regression ? "yes" : "no"}</li>
            <li>
              This signal intentionally asks whether the app looks unstable even
              when dependencies are healthy.
            </li>
          </ul>
          <a href={data.links.loki} rel="noreferrer" target="_blank">
            Investigate release behavior in Loki Explore
          </a>
        </div>

        <div className="panel operations-panel">
          <h3>Investigation shortcuts</h3>
          <ul className="link-list">
            <li>
              <a href={data.links.grafana_service_health} rel="noreferrer" target="_blank">
                Grafana: Service Health
              </a>
            </li>
            <li>
              <a href={data.links.grafana_tenant_impact} rel="noreferrer" target="_blank">
                Grafana: Tenant Impact
              </a>
            </li>
            <li>
              <a href={data.links.grafana_auth_security} rel="noreferrer" target="_blank">
                Grafana: Auth and Security
              </a>
            </li>
            <li>
              <a href={data.links.prometheus} rel="noreferrer" target="_blank">
                Prometheus: raw metrics and target checks
              </a>
            </li>
            <li>
              <a href={data.links.loki} rel="noreferrer" target="_blank">
                Loki Explore: detailed event investigation
              </a>
            </li>
            <li>
              <a href={data.links.uptime_kuma} rel="noreferrer" target="_blank">
                Uptime Kuma: dependency uptime and outage view
              </a>
            </li>
            <li>
              <a href={data.links.minio_console} rel="noreferrer" target="_blank">
                MinIO console: object storage inspection
              </a>
            </li>
          </ul>
        </div>

        <div className="panel operations-panel">
          <h3>Loki quick-start</h3>
          <p className="muted">
            Use these filters when the summary shows security churn or a
            worker-side export problem.
          </p>
          <code className="query-block">{`{compose_service="api"} | json | event_name="auth.token_rejected"`}</code>
          <code className="query-block">{`{compose_service="api"} | json | event_name="job.read_denied"`}</code>
          <code className="query-block">{`{compose_service="worker"} | json | tenant_id="${tenant.activeTenantId}"`}</code>
        </div>
      </div>
    </section>
  );
}
