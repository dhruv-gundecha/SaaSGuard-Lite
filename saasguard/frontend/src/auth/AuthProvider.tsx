import {
  PropsWithChildren,
  createContext,
  useContext,
  useEffect,
  useState,
} from "react";
import { initializeKeycloak, keycloak } from "../lib/keycloak";

interface AuthContextValue {
  authenticated: boolean;
  initializing: boolean;
  error: string | null;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  getAccessToken: () => Promise<string>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [initializing, setInitializing] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function initialize() {
      try {
        const isAuthenticated = await initializeKeycloak();
        if (!cancelled) {
          setAuthenticated(isAuthenticated);
          setError(null);
        }
      } catch (caught) {
        if (!cancelled) {
          setAuthenticated(false);
          setError(
            caught instanceof Error
              ? caught.message
              : "Keycloak initialization failed",
          );
        }
      } finally {
        if (!cancelled) {
          setInitializing(false);
        }
      }
    }

    void initialize();
    return () => {
      cancelled = true;
    };
  }, []);

  const value: AuthContextValue = {
    authenticated,
    initializing,
    error,
    login: async () => {
      await keycloak.login();
    },
    logout: async () => {
      await keycloak.logout({
        redirectUri: window.location.origin + "/",
      });
    },
    getAccessToken: async () => {
      const refreshed = await keycloak.updateToken(30).catch(() => false);
      if (!refreshed && !keycloak.token) {
        throw new Error("Authentication session is unavailable");
      }
      // The token stays in the Keycloak adapter memory and is not persisted to local storage.
      return keycloak.token as string;
    },
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
