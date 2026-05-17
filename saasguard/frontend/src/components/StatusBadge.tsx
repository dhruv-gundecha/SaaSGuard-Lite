import { JobStatus } from "../lib/types";

export function StatusBadge({
  status,
}: {
  status: JobStatus | "denied" | "success" | "healthy" | "degraded" | "unhealthy";
}) {
  return <span className={`status-badge status-${status}`}>{status.replace("_", " ")}</span>;
}
