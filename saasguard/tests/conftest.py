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
        memberships=(
            {
                "tenant_id": "tenant_beta",
                "tenant_name": "Tenant Beta",
                "role": "analyst",
            },
        ),
    )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr("src.api.bootstrap_database", lambda: None)
    monkeypatch.setattr("src.api.ensure_dev_seed_data", lambda: None)
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
