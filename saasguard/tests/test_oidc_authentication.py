from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt import InvalidTokenError
from jwt.algorithms import RSAAlgorithm

from src.auth import validate_oidc_issuer_contract
from src.metrics import api_auth_failures_total


@pytest.fixture
def oidc_settings():
    return SimpleNamespace(
        oidc_issuer="https://auth.example.test/realms/saasguard",
        oidc_audience="saasguard-api",
        oidc_algorithms=("RS256",),
        oidc_jwks_url="https://auth.example.test/realms/saasguard/protocol/openid-connect/certs",
        environment="test",
    )


@pytest.fixture
def rsa_private_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def alternate_rsa_private_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def key_id() -> str:
    return "test-key-1"


@pytest.fixture
def jwks(rsa_private_key, key_id: str) -> dict:
    public_jwk = json.loads(RSAAlgorithm.to_jwk(rsa_private_key.public_key()))
    public_jwk.update({"kid": key_id, "alg": "RS256", "use": "sig"})
    return {"keys": [public_jwk]}


class FakeJwkClient:
    def __init__(self, jwks: dict):
        self._keys: dict[str, object] = {}
        for jwk in jwks["keys"]:
            public_key = RSAAlgorithm.from_jwk(json.dumps(jwk))
            self._keys[jwk["kid"]] = public_key

    def get_signing_key_from_jwt(self, token: str):
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if kid not in self._keys:
            raise InvalidTokenError(f"Unable to find signing key for kid={kid!r}")
        return SimpleNamespace(key=self._keys[kid])


@pytest.fixture
def valid_token_factory(oidc_settings, key_id: str, rsa_private_key):
    def _build_token(
        *,
        claim_overrides: dict | None = None,
        headers_overrides: dict | None = None,
        signing_key=None,
    ) -> str:
        now = datetime.now(UTC)
        claims = {
            "iss": oidc_settings.oidc_issuer,
            "aud": oidc_settings.oidc_audience,
            "sub": "kc-alice",
            "preferred_username": "alice",
            "email": "alice@example.com",
            "iat": now,
            "exp": now + timedelta(minutes=15),
        }
        if claim_overrides:
            for key, value in claim_overrides.items():
                if value is None:
                    claims.pop(key, None)
                else:
                    claims[key] = value
        headers = {"kid": key_id}
        if headers_overrides:
            headers.update(headers_overrides)
        return jwt.encode(
            claims,
            signing_key or rsa_private_key,
            algorithm="RS256",
            headers=headers,
        )

    return _build_token


@pytest.fixture
def oidc_user_record():
    return {
        "id": uuid4(),
        "username": "alice",
        "email": "alice@example.com",
        "internal_role": None,
    }


@pytest.fixture
def oidc_auth_context(monkeypatch, oidc_settings, jwks, oidc_user_record):
    monkeypatch.setattr("src.auth.get_settings", lambda: oidc_settings)
    monkeypatch.setattr("src.auth.get_jwk_client", lambda: FakeJwkClient(jwks))
    monkeypatch.setattr("src.auth.resolve_user_by_identity", lambda **kwargs: oidc_user_record)
    monkeypatch.setattr(
        "src.auth.get_active_memberships_for_user",
        lambda user_id: [
            {
                "tenant_id": "tenant_alpha",
                "tenant_name": "Tenant Alpha",
                "role": "analyst",
            }
        ],
    )


def test_valid_jwt_is_accepted(client, oidc_auth_context, valid_token_factory):
    response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {valid_token_factory()}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["keycloak_sub"] == "kc-alice"
    assert payload["user"]["username"] == "alice"
    assert payload["active_tenant"]["tenant_id"] == "tenant_alpha"


def test_wrong_issuer_token_is_rejected(
    client,
    oidc_auth_context,
    valid_token_factory,
    caplog: pytest.LogCaptureFixture,
):
    before = api_auth_failures_total._value.get()

    with caplog.at_level(logging.WARNING):
        response = client.get(
            "/me",
            headers={
                "Authorization": (
                    "Bearer "
                    + valid_token_factory(
                        claim_overrides={"iss": "https://staging-auth.example.test/realms/saasguard"}
                    )
                )
            },
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid bearer token"}
    assert api_auth_failures_total._value.get() >= before + 1
    rejected_events = [
        record
        for record in caplog.records
        if getattr(record, "event_name", "") == "auth.token_rejected"
    ]
    assert rejected_events
    assert rejected_events[-1].error_type == "InvalidIssuerError"


def test_wrong_audience_token_is_rejected(client, oidc_auth_context, valid_token_factory):
    response = client.get(
        "/me",
        headers={
            "Authorization": (
                "Bearer "
                + valid_token_factory(claim_overrides={"aud": "wrong-audience"})
            )
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid bearer token"}


def test_expired_token_is_rejected(client, oidc_auth_context, valid_token_factory):
    past = datetime.now(UTC) - timedelta(minutes=10)
    response = client.get(
        "/me",
        headers={
            "Authorization": (
                "Bearer "
                + valid_token_factory(
                    claim_overrides={
                        "iat": past - timedelta(minutes=5),
                        "exp": past,
                    }
                )
            )
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid bearer token"}


def test_invalid_signature_token_is_rejected(
    client,
    oidc_auth_context,
    valid_token_factory,
    alternate_rsa_private_key,
):
    response = client.get(
        "/me",
        headers={
            "Authorization": (
                "Bearer "
                + valid_token_factory(signing_key=alternate_rsa_private_key)
            )
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid bearer token"}


def test_missing_subject_token_is_rejected(client, oidc_auth_context, valid_token_factory):
    response = client.get(
        "/me",
        headers={
            "Authorization": (
                "Bearer " + valid_token_factory(claim_overrides={"sub": None})
            )
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid bearer token"}


def test_oidc_issuer_contract_detects_discovery_mismatch(monkeypatch, oidc_settings):
    monkeypatch.setattr("src.auth.get_settings", lambda: oidc_settings)
    monkeypatch.setattr(
        "src.auth.fetch_oidc_discovery_document",
        lambda: {"issuer": "https://wrong-auth.example.test/realms/saasguard"},
    )

    with pytest.raises(ValueError, match="OIDC issuer contract mismatch"):
        validate_oidc_issuer_contract()

