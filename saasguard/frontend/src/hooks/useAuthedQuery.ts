import { useEffect, useState } from "react";
import { apiRequest, ApiError } from "../lib/api";
import { useAuth } from "../auth/AuthProvider";
import { useTenant } from "../tenant/TenantProvider";

interface QueryState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useAuthedQuery<T>(
  path: string | null,
  options?: {
    pollMs?: number;
  },
): QueryState<T> {
  const auth = useAuth();
  const tenant = useTenant();
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(Boolean(path));
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    if (!path || !auth.authenticated) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const accessToken = await auth.getAccessToken();
      const payload = await apiRequest<T>(path, {
        accessToken,
        activeTenantId: tenant.activeTenantId,
      });
      setData(payload);
    } catch (caught) {
      if (caught instanceof ApiError) {
        setError(caught.message);
      } else {
        setError(caught instanceof Error ? caught.message : "Request failed");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, [path, auth.authenticated, tenant.activeTenantId]);

  useEffect(() => {
    if (!options?.pollMs || !path) {
      return;
    }
    const timer = window.setInterval(() => {
      void refresh();
    }, options.pollMs);
    return () => window.clearInterval(timer);
  }, [options?.pollMs, path, auth.authenticated, tenant.activeTenantId]);

  return { data, loading, error, refresh };
}
