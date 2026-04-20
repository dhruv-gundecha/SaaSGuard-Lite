import { useParams } from "react-router-dom";
import { CopyButton } from "../components/CopyButton";
import { EmptyState } from "../components/EmptyState";
import { ErrorPanel } from "../components/ErrorPanel";
import { LoadingState } from "../components/LoadingState";
import { StatusBadge } from "../components/StatusBadge";
import { useAuthedQuery } from "../hooks/useAuthedQuery";
import { formatDateTime } from "../lib/format";
import { AuditResponse, ExportJob } from "../lib/types";
import { useTenant } from "../tenant/TenantProvider";

export function JobDetailPage() {
  const { jobId } = useParams();
  const tenant = useTenant();
  const job = useAuthedQuery<ExportJob>(
    tenant.activeTenantId && jobId ? `/jobs/${jobId}` : null,
    { pollMs: 10000 },
  );
  const audit = useAuthedQuery<AuditResponse>(
    tenant.activeTenantId ? "/audit-events?limit=20" : null,
  );

  const relatedEvents =
    audit.data?.events.filter(
      (event) =>
        event.target_id === jobId || event.correlation_id === job.data?.correlation_id,
    ) ?? [];

  return (
    <section className="page-section">
      <div className="page-header">
        <div>
          <span className="eyebrow">Job detail</span>
          <h2>Export job inspection</h2>
        </div>
      </div>

      {!jobId ? (
        <EmptyState title="Missing job" description="No job identifier was supplied in the route." />
      ) : job.loading ? (
        <LoadingState label="Loading job detail" />
      ) : job.error ? (
        <ErrorPanel
          title="Job access failed"
          message={job.error}
        />
      ) : !job.data ? (
        <EmptyState title="Job not found" description="The selected job could not be loaded." />
      ) : (
        <>
          <div className="grid two-column">
            <div className="panel">
              <div className="panel-header-inline">
                <h3>Job record</h3>
                <StatusBadge status={job.data.status} />
              </div>
              <dl className="detail-grid">
                <div>
                  <dt>Job ID</dt>
                  <dd>
                    {job.data.job_id} <CopyButton value={job.data.job_id} />
                  </dd>
                </div>
                <div>
                  <dt>Tenant ID</dt>
                  <dd>{job.data.tenant_id}</dd>
                </div>
                <div>
                  <dt>Requester</dt>
                  <dd>{job.data.requester_user_id}</dd>
                </div>
                <div>
                  <dt>Correlation ID</dt>
                  <dd>
                    {job.data.correlation_id} <CopyButton value={job.data.correlation_id} />
                  </dd>
                </div>
                <div>
                  <dt>Created</dt>
                  <dd>{formatDateTime(job.data.created_at)}</dd>
                </div>
                <div>
                  <dt>Updated</dt>
                  <dd>{formatDateTime(job.data.updated_at)}</dd>
                </div>
                <div>
                  <dt>Object key</dt>
                  <dd>{job.data.object_key ?? "Not available"}</dd>
                </div>
                <div>
                  <dt>Failure stage</dt>
                  <dd>{job.data.failure_stage ?? "Not available"}</dd>
                </div>
              </dl>
              {job.data.error_message ? (
                <div className="stack-block">
                  <h4>Failure detail</h4>
                  <p className="error-copy">{job.data.error_message}</p>
                </div>
              ) : null}
            </div>

            <div className="panel">
              <h3>Event timeline</h3>
              {!relatedEvents.length ? (
                <EmptyState
                  title="No related audit events"
                  description="Audit event access is limited to tenant_admin. If you are not an admin, only the job record is available."
                />
              ) : (
                <ul className="timeline">
                  {relatedEvents.map((event) => (
                    <li key={event.id}>
                      <span>{formatDateTime(event.event_time)}</span>
                      <strong>{event.action}</strong>
                      <p>
                        outcome: {event.outcome}
                        {event.reason ? `, reason: ${event.reason}` : ""}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </>
      )}
    </section>
  );
}
