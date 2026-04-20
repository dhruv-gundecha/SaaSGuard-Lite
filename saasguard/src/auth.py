import logging
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Header, HTTPException, status
from jwt import InvalidTokenError, PyJWKClient

from src.config import get_settings
from src.db import get_active_memberships_for_user, resolve_user_by_identity
from src.logging_utils import log_event


logger = logging.getLogger("saasguard.auth")


@dataclass(frozen=True)
class IdentityClaims:
    sub: str
    preferred_username: str | None
    email: str | None


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    keycloak_sub: str
    username: str
    email: str | None
    memberships: tuple[dict, ...]


@lru_cache
def get_jwk_client() -> PyJWKClient:
    return PyJWKClient(get_settings().oidc_jwks_url)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise _unauthorized("Missing bearer token")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise _unauthorized("Invalid authorization header")
    return token


def validate_access_token(token: str) -> IdentityClaims:
    settings = get_settings()
    try:
        signing_key = get_jwk_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            key=signing_key.key,
            algorithms=list(settings.oidc_algorithms),
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
    except InvalidTokenError as exc:
        log_event(
            logger,
            logging.WARNING,
            "auth.token_rejected",
            "access token rejected",
            outcome="denied",
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        raise _unauthorized("Invalid bearer token") from exc

    log_event(
        logger,
        logging.INFO,
        "auth.token_validated",
        "access token validated",
        outcome="success",
        keycloak_sub=claims["sub"],
    )
    return IdentityClaims(
        sub=claims["sub"],
        preferred_username=claims.get("preferred_username"),
        email=claims.get("email"),
    )


def get_current_user(authorization: str | None = Header(default=None)) -> AuthenticatedUser:
    token = _extract_bearer_token(authorization)
    identity = validate_access_token(token)
    user = resolve_user_by_identity(
        keycloak_sub=identity.sub,
        username=identity.preferred_username,
        email=identity.email,
    )
    if not user:
        log_event(
            logger,
            logging.WARNING,
            "auth.user_resolved",
            "internal user mapping failed",
            outcome="denied",
            keycloak_sub=identity.sub,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not provisioned for SaaSGuard",
        )

    memberships = tuple(get_active_memberships_for_user(str(user["id"])))
    if not memberships:
        log_event(
            logger,
            logging.WARNING,
            "auth.membership_resolved",
            "no active memberships available",
            outcome="denied",
            user_id=str(user["id"]),
            keycloak_sub=identity.sub,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have an active tenant membership",
        )

    log_event(
        logger,
        logging.INFO,
        "auth.user_resolved",
        "internal user resolved",
        outcome="success",
        user_id=str(user["id"]),
        keycloak_sub=identity.sub,
    )

    return AuthenticatedUser(
        user_id=str(user["id"]),
        keycloak_sub=identity.sub,
        username=user["username"],
        email=user["email"],
        memberships=memberships,
    )
