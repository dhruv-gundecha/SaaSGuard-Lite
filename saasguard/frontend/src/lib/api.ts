import { env } from "./env";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

interface RequestOptions {
  accessToken: string;
  activeTenantId?: string | null;
  method?: string;
  body?: unknown;
  signal?: AbortSignal;
}

function buildHeaders(options: RequestOptions) {
  const headers = new Headers({
    Authorization: `Bearer ${options.accessToken}`,
  });

  if (options.activeTenantId) {
    headers.set("X-Active-Tenant", options.activeTenantId);
  }
  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  return headers;
}

async function performRequest(path: string, options: RequestOptions) {
  const response = await fetch(`${env.apiBaseUrl}${path}`, {
    method: options.method ?? "GET",
    headers: buildHeaders(options),
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    signal: options.signal,
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null;
    throw new ApiError(payload?.detail ?? "Request failed", response.status);
  }

  return response;
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions,
): Promise<T> {
  const response = await performRequest(path, options);

  return (await response.json()) as T;
}

function parseAttachmentFilename(contentDisposition: string | null): string | null {
  if (!contentDisposition) {
    return null;
  }
  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match) {
    return decodeURIComponent(utf8Match[1]);
  }
  const plainMatch = contentDisposition.match(/filename="([^"]+)"/i);
  if (plainMatch) {
    return plainMatch[1];
  }
  return null;
}

export async function apiDownload(
  path: string,
  options: RequestOptions,
): Promise<{ blob: Blob; filename: string | null }> {
  const response = await performRequest(path, options);
  return {
    blob: await response.blob(),
    filename: parseAttachmentFilename(response.headers.get("Content-Disposition")),
  };
}
