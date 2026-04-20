import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider";
import { ErrorPanel } from "../components/ErrorPanel";
import { LoadingState } from "../components/LoadingState";

export function LoginPage() {
  const auth = useAuth();

  if (auth.initializing) {
    return <LoadingState label="Initializing sign-in" />;
  }
  if (auth.authenticated) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <span className="eyebrow">Local demo console</span>
        <h1>SaaSGuard-Lite UI</h1>
        <p>
          Authenticate through Keycloak, select tenant context, request exports,
          inspect async job state, and review operational signals.
        </p>

        <div className="seed-accounts">
          <div>
            <strong>Seeded users</strong>
            <p>`alice`, `bob`, and multi-tenant `carol` are available with seeded tenants and demo job history.</p>
          </div>
        </div>

        {auth.error ? (
          <ErrorPanel
            title="Authentication startup failed"
            message={auth.error}
          />
        ) : null}

        <button className="primary-button login-button" onClick={() => void auth.login()} type="button">
          Sign in with Keycloak
        </button>
      </div>
    </div>
  );
}
