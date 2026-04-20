import { Link } from "react-router-dom";
import { useState } from "react";
import { EmptyState } from "../components/EmptyState";
import { ErrorPanel } from "../components/ErrorPanel";
import { LoadingState } from "../components/LoadingState";
import { StatusBadge } from "../components/StatusBadge";
import { useAuthedQuery } from "../hooks/useAuthedQuery";
import { formatDateTime, summarizeError } from "../lib/format";
import { JobsResponse } from "../lib/types";
import { useTenant } from "../tenant/TenantProvider";

const statusOptions = ["all", "queued", "retry_pending", "processing", "completed", "failed"] as const;
const timeOptions = [
  { label: "24 hours", value: 24 },
  { label: "72 hours", value: 72 },
  { label: "7 days", value: 168 },
];

export function JobsPage() {
  const tenant = useTenant();
  const [status, setStatus] = useState<(typeof statusOptions)[number]>("all");
  const [hours, setHours] = useState(168);
  const search = new URLSearchParams({ hours: String(hours) });
  if (status !== "all") {
    search.set("status", status);
  }
  const query =
    tenant.activeTenantId ? `/jobs?${search.toString()}` : null;
  const jobs = useAuthedQuery<JobsResponse>(query, { pollMs: 10000 });

  return (
    <section className="page-section">
      <div className="page-header">
        <div>
          <span className="eyebrow">Jobs</span>
          <h2>Tenant-scoped job history</h2>
          <p className="muted">
            Only jobs for <strong>{tenant.activeMembership?.tenant_name ?? "the active tenant"}</strong> are shown.
          </p>
        </div>
        <div className="filters">
          <select value={status} onChange={(event) => setStatus(event.target.value as typeof status)}>
            {statusOptions.map((option) => (
              <option key={option} value={option}>
                Status: {option}
              </option>
            ))}
          </select>
          <select value={hours} onChange={(event) => setHours(Number(event.target.value))}>
            {timeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                Window: {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {!tenant.activeTenantId ? (
        <EmptyState
          title="No tenant selected"
          description="Select a tenant to load the recent jobs list."
        />
      ) : jobs.loading ? (
        <LoadingState label="Loading recent jobs" />
      ) : jobs.error ? (
        <ErrorPanel message={jobs.error} />
      ) : !jobs.data?.items.length ? (
        <EmptyState
          title="No jobs in this window"
          description="Create an export or expand the time window to view older jobs."
        />
      ) : (
        <div className="table-panel">
          <table className="data-table">
            <thead>
              <tr>
                <th>Job</th>
                <th>Created</th>
                <th>Requester</th>
                <th>Tenant</th>
                <th>Status</th>
                <th>Object key</th>
                <th>Error summary</th>
              </tr>
            </thead>
            <tbody>
              {jobs.data.items.map((job) => (
                <tr key={job.job_id}>
                  <td>
                    <Link className="table-link" to={`/jobs/${job.job_id}`}>
                      {job.job_id.slice(0, 8)}...
                    </Link>
                  </td>
                  <td>{formatDateTime(job.created_at)}</td>
                  <td>{job.requester_username ?? job.requester_user_id}</td>
                  <td>{job.tenant_id}</td>
                  <td>
                    <StatusBadge status={job.status} />
                  </td>
                  <td>{job.object_key ?? "Pending"}</td>
                  <td>{summarizeError(job.error_message)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
