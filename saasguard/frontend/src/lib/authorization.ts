import type { SessionResponse } from "./types";

export function canAccessOperations(session: SessionResponse | null): boolean {
  return session?.authorization.can_access_operations ?? false;
}

export function isOperationsNavVisible(session: SessionResponse | null): boolean {
  return canAccessOperations(session);
}
