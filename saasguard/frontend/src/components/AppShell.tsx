import { NavLink, Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider";
import { isOperationsNavVisible } from "../lib/authorization";
import { LoadingState } from "./LoadingState";
import { useTenant } from "../tenant/TenantProvider";
import { ErrorPanel } from "./ErrorPanel";

const navigation = [
  { to: "/", label: "Dashboard" },
  { to: "/exports", label: "Exports" },
  { to: "/jobs", label: "Jobs" },
  { to: "/audit", label: "Audit" },
  { to: "/operations", label: "Operations" },
] as const;

export function AppShell() {
  const auth = useAuth();
  const tenant = useTenant();
  const operationsVisible = isOperationsNavVisible(tenant.session);
  const visibleNavigation = navigation.filter(
    (item) => item.to !== "/operations" || operationsVisible,
  );

  if (auth.initializing) {
    return <LoadingState label="Redirecting to Keycloak" />;
  }
  if (!auth.authenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-panel">
          <span className="eyebrow">Secure export console</span>
          <h1>SaaSGuard-Lite</h1>
          <p>
            Tenant-aware export workflows with explicit identity, authorization,
            and operational context.
          </p>
        </div>

        <nav className="nav-list">
          {visibleNavigation.map((item) => (
            <NavLink
              className={({ isActive }) =>
                isActive ? "nav-link nav-link-active" : "nav-link"
              }
              key={item.to}
              to={item.to}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="content">
        <header className="topbar">
          <div>
            <span className="eyebrow">Identity</span>
            <div className="identity-block">
              <strong>{tenant.session?.user.username ?? "Unknown user"}</strong>
              <span>{tenant.session?.user.email ?? "No email"}</span>
              {tenant.session?.user.internal_role ? (
                <small>Internal role: {tenant.session.user.internal_role}</small>
              ) : null}
            </div>
          </div>

          <div className="tenant-switcher">
            <span className="eyebrow">Active tenant</span>
            {tenant.loading ? (
              <span>Loading context...</span>
            ) : (tenant.session?.memberships.length ?? 0) === 0 ? (
              <div className="tenant-pill">
                No tenant scope
                <small>Internal-only session</small>
              </div>
            ) : tenant.session?.memberships.length === 1 ? (
              <div className="tenant-pill">
                {tenant.session.active_tenant?.tenant_name}
                <small>{tenant.session.active_tenant?.role}</small>
              </div>
            ) : (
              <select
                aria-label="Active tenant"
                className="tenant-select"
                onChange={(event) => tenant.setActiveTenantId(event.target.value)}
                value={tenant.activeTenantId ?? ""}
              >
                <option value="" disabled>
                  Choose tenant
                </option>
                {tenant.session?.memberships.map((membership) => (
                  <option key={membership.tenant_id} value={membership.tenant_id}>
                    {membership.tenant_name} ({membership.role})
                  </option>
                ))}
              </select>
            )}
          </div>

          <button className="primary-button" onClick={() => void auth.logout()} type="button">
            Logout
          </button>
        </header>

        {tenant.error ? <ErrorPanel title="Tenant context required" message={tenant.error} /> : null}
        <Outlet />
      </main>
    </div>
  );
}
