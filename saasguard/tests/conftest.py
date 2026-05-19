from collections.abc import Iterator
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api import app
from src.auth import AuthenticatedUser


@pytest.fixture
def alice_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id="user-alice",
        keycloak_sub="kc-alice",
        username="alice",
        email="alice@example.com",
        internal_role=None,
        memberships=(
            {
                "tenant_id": "tenant_alpha",
                "tenant_name": "Tenant Alpha",
                "role": "analyst",
            },
        ),
    )


@pytest.fixture
def bob_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id="user-bob",
        keycloak_sub="kc-bob",
        username="bob",
        email="bob@example.com",
        internal_role=None,
        memberships=(
            {
                "tenant_id": "tenant_beta",
                "tenant_name": "Tenant Beta",
                "role": "analyst",
            },
        ),
    )


@pytest.fixture
def viewer_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id="user-viewer",
        keycloak_sub="kc-viewer",
        username="victor",
        email="victor@example.com",
        internal_role=None,
        memberships=(
            {
                "tenant_id": "tenant_gamma",
                "tenant_name": "Tenant Gamma",
                "role": "viewer",
            },
        ),
    )


@pytest.fixture
def carol_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id="user-carol",
        keycloak_sub="kc-carol",
        username="carol",
        email="carol@example.com",
        internal_role=None,
        memberships=(
            {
                "tenant_id": "tenant_alpha",
                "tenant_name": "Tenant Alpha",
                "role": "tenant_admin",
            },
            {
                "tenant_id": "tenant_beta",
                "tenant_name": "Tenant Beta",
                "role": "tenant_admin",
            },
        ),
    )


@pytest.fixture
def soc_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id="user-soc",
        keycloak_sub="kc-soc",
        username="soc",
        email="soc@example.com",
        internal_role="soc_admin",
        memberships=(),
    )


@pytest.fixture
def ops_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id="user-ops",
        keycloak_sub="kc-ops",
        username="ops",
        email="ops@example.com",
        internal_role="ops_admin",
        memberships=(),
    )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr("src.api.bootstrap_database", lambda: None)
    monkeypatch.setattr("src.api.ensure_dev_seed_data", lambda: None)
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
