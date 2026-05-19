import test from "node:test";
import assert from "node:assert/strict";

import { canAccessOperations, isOperationsNavVisible } from "../.tmp-authz-test/authorization.js";

function session(overrides = {}) {
  return {
    user: {
      id: "user-1",
      keycloak_sub: "kc-1",
      username: "user",
      email: "user@example.com",
      internal_role: null,
    },
    active_tenant: null,
    memberships: [],
    authorization: {
      can_access_operations: false,
    },
    ...overrides,
  };
}

test("tenant_admin cannot see operations navigation", () => {
  const tenantAdminSession = session({
    memberships: [
      {
        tenant_id: "tenant_alpha",
        tenant_name: "Tenant Alpha",
        role: "tenant_admin",
      },
    ],
    active_tenant: {
      tenant_id: "tenant_alpha",
      tenant_name: "Tenant Alpha",
      role: "tenant_admin",
    },
  });

  assert.equal(canAccessOperations(tenantAdminSession), false);
  assert.equal(isOperationsNavVisible(tenantAdminSession), false);
});

test("soc_admin can see operations navigation", () => {
  const socSession = session({
    user: {
      id: "user-soc",
      keycloak_sub: "kc-soc",
      username: "soc",
      email: "soc@example.com",
      internal_role: "soc_admin",
    },
    authorization: {
      can_access_operations: true,
    },
  });

  assert.equal(canAccessOperations(socSession), true);
  assert.equal(isOperationsNavVisible(socSession), true);
});
