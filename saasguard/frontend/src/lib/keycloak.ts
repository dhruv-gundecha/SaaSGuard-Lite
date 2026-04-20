import Keycloak from "keycloak-js";
import { env } from "./env";

export const keycloak = new Keycloak({
  url: env.keycloakUrl,
  realm: env.keycloakRealm,
  clientId: env.keycloakClientId,
});

let keycloakInitPromise: Promise<boolean> | null = null;

export function initializeKeycloak(): Promise<boolean> {
  if (!keycloakInitPromise) {
    keycloakInitPromise = keycloak.init({
      onLoad: "login-required",
      pkceMethod: "S256",
      checkLoginIframe: false,
    });
  }

  return keycloakInitPromise;
}
