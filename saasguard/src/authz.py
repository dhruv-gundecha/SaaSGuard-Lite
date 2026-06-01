import logging
from dataclasses import dataclass

from fastapi import Header, HTTPException, status

from src.auth import AuthenticatedUser
from src.db import record_audit_event
from src.logging_utils import log_event
from src.metrics import api_tenant_authorization_denials_total, tenant_metric_labels


logger = logging.getLogger("saasguard.authz")
ROLE_ORDER = {"viewer": 1, "analyst": 2, "tenant_admin": 3}
OPERATIONS_INTERNAL_ROLES = {"soc_admin", "ops_admin"}


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    tenant_name: str
    role: str


def record_tenant_authorization_denial(
    *,
    user: AuthenticatedUser,
    tenant_id: str,
    correlation_id: str,
    denied_action: str,
    target_type: str,
    target_id: str | None,
    reason: str,
    event_name: str = "auth.authorization_denied",
    message: str = "tenant-scoped authorization denied",
) -> None:
    record_audit_event(
        actor_user_id=user.user_id,
        actor_sub=user.keycloak_sub,
        tenant_id=tenant_id,
        action="authorization.denied",
        target_type=target_type,
        target_id=target_id,
        outcome="denied",
        reason=f"{denied_action}: {reason}",
        correlation_id=correlation_id,
    )
    api_tenant_authorization_denials_total.labels(
        action=denied_action, **tenant_metric_labels(tenant_id)
    ).inc()
    log_event(
        logger,
        logging.WARNING,
        event_name,
        message,
        tenant_id=tenant_id,
        user_id=user.user_id,
        keycloak_sub=user.keycloak_sub,
        correlation_id=correlation_id,
        outcome="denied",
        error_message=reason,
    )


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

    record_tenant_authorization_denial(
        user=user,
        tenant_id=tenant.tenant_id,
        correlation_id=correlation_id,
        denied_action=action,
        target_type="tenant",
        target_id=tenant.tenant_id,
        reason=f"role {tenant.role} cannot perform action requiring {minimum_role}",
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="User does not have sufficient permissions",
    )


def can_access_operations(user: AuthenticatedUser) -> bool:
    return user.internal_role in OPERATIONS_INTERNAL_ROLES


def require_operations_role(
    *,
    user: AuthenticatedUser,
    correlation_id: str,
    action: str,
) -> None:
    if can_access_operations(user):
        return

    record_audit_event(
        actor_user_id=user.user_id,
        actor_sub=user.keycloak_sub,
        tenant_id=None,
        action=action,
        target_type="operations_overview",
        target_id="global",
        outcome="denied",
        reason=f"internal role {user.internal_role or 'none'} cannot access global operations",
        correlation_id=correlation_id,
    )
    log_event(
        logger,
        logging.WARNING,
        "auth.operations_denied",
        "global operations access denied",
        user_id=user.user_id,
        keycloak_sub=user.keycloak_sub,
        correlation_id=correlation_id,
        outcome="denied",
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="User does not have sufficient permissions",
    )
