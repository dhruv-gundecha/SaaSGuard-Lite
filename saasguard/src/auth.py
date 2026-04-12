from dataclasses import dataclass

from fastapi import Header, HTTPException, status


USER_TENANT_MAP = {
    "alice": "tenant_alpha",
    "bob": "tenant_beta",
}


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    tenant_id: str


def get_current_user(x_user: str | None = Header(default=None)) -> AuthenticatedUser:
    if not x_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User header",
        )

    tenant_id = USER_TENANT_MAP.get(x_user)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unknown user",
        )

    return AuthenticatedUser(user_id=x_user, tenant_id=tenant_id)
