import {
  PropsWithChildren,
  createContext,
  useContext,
  useEffect,
  useState,
} from "react";
import { ApiError, apiRequest } from "../lib/api";
import { Membership, SessionResponse } from "../lib/types";
import { useAuth } from "../auth/AuthProvider";

const ACTIVE_TENANT_KEY = "saasguard.activeTenantId";

interface TenantContextValue {
  session: SessionResponse | null;
  activeTenantId: string | null;
  activeMembership: Membership | null;
  loading: boolean;
  error: string | null;
  refreshSession: () => Promise<void>;
  setActiveTenantId: (tenantId: string) => void;
}

const TenantContext = createContext<TenantContextValue | null>(null);

export function TenantProvider({ children }: PropsWithChildren) {
  const auth = useAuth();
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [activeTenantId, setActiveTenantIdState] = useState<string | null>(
    sessionStorage.getItem(ACTIVE_TENANT_KEY),
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refreshSession() {
    if (!auth.authenticated) {
      setSession(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const accessToken = await auth.getAccessToken();
      const nextSession = await apiRequest<SessionResponse>("/me", {
        accessToken,
        activeTenantId,
      });

      const resolvedTenantId =
        nextSession.active_tenant?.tenant_id ??
        nextSession.memberships[0]?.tenant_id ??
        null;

      if (resolvedTenantId && resolvedTenantId !== activeTenantId) {
        sessionStorage.setItem(ACTIVE_TENANT_KEY, resolvedTenantId);
        setActiveTenantIdState(resolvedTenantId);
      }

      setSession(nextSession);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 403 && activeTenantId) {
        sessionStorage.removeItem(ACTIVE_TENANT_KEY);
        setActiveTenantIdState(null);
        return;
      }
      if (caught instanceof ApiError && caught.status === 400) {
        setSession(null);
        setError(caught.message);
        return;
      }
      setError(caught instanceof Error ? caught.message : "Failed to load session");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refreshSession();
  }, [auth.authenticated, activeTenantId]);

  function setActiveTenantId(tenantId: string) {
    sessionStorage.setItem(ACTIVE_TENANT_KEY, tenantId);
    setActiveTenantIdState(tenantId);
  }

  const activeMembership =
    session?.memberships.find((membership) => membership.tenant_id === activeTenantId) ??
    session?.active_tenant ??
    null;

  return (
    <TenantContext.Provider
      value={{
        session,
        activeTenantId,
        activeMembership,
        loading,
        error,
        refreshSession,
        setActiveTenantId,
      }}
    >
      {children}
    </TenantContext.Provider>
  );
}

export function useTenant() {
  const context = useContext(TenantContext);
  if (!context) {
    throw new Error("useTenant must be used within TenantProvider");
  }
  return context;
}
