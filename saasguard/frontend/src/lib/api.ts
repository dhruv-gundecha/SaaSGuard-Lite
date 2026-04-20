import { env } from "./env";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function apiRequest<T>(
  path: string,
  options: {
    accessToken: string;
    activeTenantId?: string | null;
    method?: string;
    body?: unknown;
    signal?: AbortSignal;
  },
): Promise<T> {
  const headers = new Headers({
    Authorization: `Bearer ${options.accessToken}`,
  });

  if (options.activeTenantId) {
    headers.set("X-Active-Tenant", options.activeTenantId);
  }
  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${env.apiBaseUrl}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    signal: options.signal,
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null;
    throw new ApiError(payload?.detail ?? "Request failed", response.status);
  }

  return (await response.json()) as T;
}
