import { useState } from "react";
import { useAuth } from "../auth/AuthProvider";
import { ErrorPanel } from "../components/ErrorPanel";
import { StatusBadge } from "../components/StatusBadge";
import { apiRequest, ApiError } from "../lib/api";
import { CreateExportResponse } from "../lib/types";
import { useTenant } from "../tenant/TenantProvider";

export function ExportsPage() {
  const auth = useAuth();
  const tenant = useTenant();
  const [result, setResult] = useState<CreateExportResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canCreate =
    tenant.activeMembership?.role === "analyst" ||
    tenant.activeMembership?.role === "tenant_admin";

  async function submitExport() {
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const accessToken = await auth.getAccessToken();
      const response = await apiRequest<CreateExportResponse>("/exports", {
        accessToken,
        activeTenantId: tenant.activeTenantId,
        method: "POST",
      });
      setResult(response);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Export request failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="page-section">
      <div className="page-header">
        <div>
          <span className="eyebrow">Exports</span>
          <h2>Create tenant-scoped exports</h2>
        </div>
      </div>

      <div className="panel panel-accent">
        <h3>Request a new export</h3>
        <p>
          The export will be created for <strong>{tenant.activeMembership?.tenant_name ?? "no tenant selected"}</strong>.
          The API stores authoritative tenant context before the worker dequeues the job.
        </p>
        <div className="hint-row">
          <span>Active role: {tenant.activeMembership?.role ?? "Unavailable"}</span>
          <span>Required role: analyst or tenant_admin</span>
        </div>

        {!canCreate ? (
          <ErrorPanel
            title="Authorization required"
            message="This tenant membership cannot request exports. Switch to a tenant with analyst or tenant_admin access."
          />
        ) : null}
        {error ? <ErrorPanel message={error} /> : null}
        {result ? (
          <div className="success-panel">
            <strong>Export request accepted</strong>
            <div className="success-grid">
              <span>Job ID: {result.job_id}</span>
              <span>
                Status: <StatusBadge status={result.status} />
              </span>
              <span>Correlation ID: {result.correlation_id}</span>
            </div>
          </div>
        ) : null}

        <button
          className="primary-button"
          disabled={!tenant.activeTenantId || !canCreate || submitting}
          onClick={() => void submitExport()}
          type="button"
        >
          {submitting ? "Submitting..." : "Request export"}
        </button>
      </div>
    </section>
  );
}
