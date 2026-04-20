import logging
from dataclasses import dataclass

from fastapi import Header, HTTPException, status

from src.auth import AuthenticatedUser
from src.db import record_audit_event
from src.logging_utils import log_event


logger = logging.getLogger("saasguard.authz")
ROLE_ORDER = {"viewer": 1, "analyst": 2, "tenant_admin": 3}


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    tenant_name: str
    role: str


def resolve_active_tenant(
    user: AuthenticatedUser,
    x_active_tenant: str | None,
) -> TenantContext:
    memberships = {membership["tenant_id"]: membership for membership in user.memberships}

    if x_active_tenant:
        membership = memberships.get(x_active_tenant)
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Requested tenant is not available for this user",
            )
        return TenantContext(
            tenant_id=membership["tenant_id"],
            tenant_name=membership["tenant_name"],
            role=membership["role"],
        )

    if len(user.memberships) == 1:
        membership = user.memberships[0]
        return TenantContext(
            tenant_id=membership["tenant_id"],
            tenant_name=membership["tenant_name"],
            role=membership["role"],
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="X-Active-Tenant header is required for multi-tenant users",
    )


def require_role(
    *,
    user: AuthenticatedUser,
    tenant: TenantContext,
    minimum_role: str,
    correlation_id: str,
    action: str,
) -> None:
    if ROLE_ORDER[tenant.role] >= ROLE_ORDER[minimum_role]:
        return

    record_audit_event(
        actor_user_id=user.user_id,
        actor_sub=user.keycloak_sub,
        tenant_id=tenant.tenant_id,
        action=action,
        target_type="tenant",
        target_id=tenant.tenant_id,
        outcome="denied",
        reason=f"role {tenant.role} cannot perform action requiring {minimum_role}",
        correlation_id=correlation_id,
    )
    log_event(
        logger,
        logging.WARNING,
        "auth.authorization_denied",
        "role authorization denied",
        tenant_id=tenant.tenant_id,
        user_id=user.user_id,
        keycloak_sub=user.keycloak_sub,
        outcome="denied",
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="User does not have sufficient permissions",
    )
