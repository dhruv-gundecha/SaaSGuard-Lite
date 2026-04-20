export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "Not available";
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatRelativeMinutes(minutes: number): string {
  if (!Number.isFinite(minutes)) {
    return "Unavailable";
  }
  if (minutes < 1) {
    return "Under 1 minute";
  }
  if (minutes < 60) {
    return `${Math.round(minutes)} minutes`;
  }
  const hours = minutes / 60;
  if (hours < 24) {
    return `${hours.toFixed(1)} hours`;
  }
  return `${(hours / 24).toFixed(1)} days`;
}

export function summarizeError(message: string | null | undefined): string {
  if (!message) {
    return "No error recorded";
  }
  return message.length > 96 ? `${message.slice(0, 93)}...` : message;
}
