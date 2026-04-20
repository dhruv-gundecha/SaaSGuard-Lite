import { JobStatus } from "../lib/types";

export function StatusBadge({ status }: { status: JobStatus | "denied" | "success" }) {
  return <span className={`status-badge status-${status}`}>{status.replace("_", " ")}</span>;
}
