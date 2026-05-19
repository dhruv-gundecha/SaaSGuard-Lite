import { Link } from "react-router-dom";
import { useState } from "react";
import { useAuth } from "../auth/AuthProvider";
import { EmptyState } from "../components/EmptyState";
import { ErrorPanel } from "../components/ErrorPanel";
import { LoadingState } from "../components/LoadingState";
import { StatusBadge } from "../components/StatusBadge";
import { useAuthedQuery } from "../hooks/useAuthedQuery";
import { apiDownload, ApiError } from "../lib/api";
import { formatDateTime, summarizeError } from "../lib/format";
import { ExportJob, JobsResponse } from "../lib/types";
import { useTenant } from "../tenant/TenantProvider";

const statusOptions = ["all", "queued", "retry_pending", "processing", "completed", "failed"] as const;
const timeOptions = [
  { label: "24 hours", value: 24 },
  { label: "72 hours", value: 72 },
  { label: "7 days", value: 168 },
];

export function JobsPage() {
  const auth = useAuth();
  const tenant = useTenant();
  const [status, setStatus] = useState<(typeof statusOptions)[number]>("all");
  const [hours, setHours] = useState(168);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [downloadingJobId, setDownloadingJobId] = useState<string | null>(null);
  const search = new URLSearchParams({ hours: String(hours) });
  if (status !== "all") {
    search.set("status", status);
  }
  const query =
    tenant.activeTenantId ? `/jobs?${search.toString()}` : null;
  const jobs = useAuthedQuery<JobsResponse>(query, { pollMs: 10000 });

  async function downloadJob(job: ExportJob) {
    setDownloadingJobId(job.job_id);
    setDownloadError(null);
    try {
      const accessToken = await auth.getAccessToken();
      const { blob, filename } = await apiDownload(`/jobs/${job.job_id}/download`, {
        accessToken,
      });
      const objectUrl = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = filename ?? `export-${job.job_id}.csv`;
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(objectUrl);
    } catch (caught) {
      setDownloadError(
        caught instanceof ApiError ? caught.message : "Export download failed",
      );
    } finally {
      setDownloadingJobId(null);
    }
  }

  function renderDownloadAction(job: ExportJob) {
    if (job.status === "completed") {
      return (
        <button
          className="ghost-button"
          disabled={downloadingJobId === job.job_id}
          onClick={() => void downloadJob(job)}
          type="button"
        >
          {downloadingJobId === job.job_id ? "Downloading..." : "Download"}
        </button>
      );
    }
    if (job.status === "queued" || job.status === "retry_pending" || job.status === "processing") {
      return (
        <button className="ghost-button" disabled type="button">
          Not ready
        </button>
      );
    }
    return <span className="muted">Unavailable</span>;
  }

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
      {downloadError ? <ErrorPanel title="Download failed" message={downloadError} /> : null}

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
                <th>Download</th>
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
                  <td>{renderDownloadAction(job)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
