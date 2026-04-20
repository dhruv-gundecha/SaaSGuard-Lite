import { EmptyState } from "../components/EmptyState";
import { ErrorPanel } from "../components/ErrorPanel";
import { LoadingState } from "../components/LoadingState";
import { StatusBadge } from "../components/StatusBadge";
import { useAuthedQuery } from "../hooks/useAuthedQuery";
import { formatDateTime } from "../lib/format";
import { AuditResponse } from "../lib/types";
import { useTenant } from "../tenant/TenantProvider";

export function AuditPage() {
  const tenant = useTenant();
  const audit = useAuthedQuery<AuditResponse>(
    tenant.activeTenantId ? "/audit-events?limit=100" : null,
  );

  return (
    <section className="page-section">
      <div className="page-header">
        <div>
          <span className="eyebrow">Audit</span>
          <h2>Tenant evidence stream</h2>
          <p className="muted">Actions like export requests, job views, and denials appear here for incident review.</p>
        </div>
      </div>

      {!tenant.activeTenantId ? (
        <EmptyState title="No tenant selected" description="Select a tenant to view audit evidence." />
      ) : audit.loading ? (
        <LoadingState label="Loading audit events" />
      ) : audit.error ? (
        <ErrorPanel
          title="Audit access not available"
          message={audit.error}
        />
      ) : !audit.data?.events.length ? (
        <EmptyState title="No audit events yet" description="Create exports or inspect jobs to generate tenant activity." />
      ) : (
        <div className="table-panel">
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Actor</th>
                <th>Tenant</th>
                <th>Action</th>
                <th>Target</th>
                <th>Outcome</th>
                <th>Correlation</th>
              </tr>
            </thead>
            <tbody>
              {audit.data.events.map((event) => (
                <tr key={event.id}>
                  <td>{formatDateTime(event.event_time)}</td>
                  <td>{event.actor_user_id ?? event.actor_sub ?? "System"}</td>
                  <td>{event.tenant_id ?? "Global"}</td>
                  <td>{event.action}</td>
                  <td>{event.target_type}:{event.target_id ?? "-"}</td>
                  <td>
                    <StatusBadge status={event.outcome === "denied" ? "denied" : "success"} />
                  </td>
                  <td>{event.correlation_id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
