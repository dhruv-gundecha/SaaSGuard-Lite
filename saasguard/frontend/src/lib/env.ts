export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
  keycloakUrl:
    import.meta.env.VITE_KEYCLOAK_URL ?? "http://auth.saasguard.local:8081",
  keycloakRealm: import.meta.env.VITE_KEYCLOAK_REALM ?? "saasguard",
  keycloakClientId:
    import.meta.env.VITE_KEYCLOAK_CLIENT_ID ?? "saasguard-frontend",
  grafanaUrl: import.meta.env.VITE_GRAFANA_URL ?? "http://localhost:3000",
  prometheusUrl:
    import.meta.env.VITE_PROMETHEUS_URL ?? "http://localhost:9090",
  lokiUrl: import.meta.env.VITE_LOKI_URL ?? "http://localhost:3100",
};
