import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def as_user(client: TestClient):
    """Return a GET helper that sends requests as the given user."""

    def get(username: str, path: str, **params):
        return client.get(path, headers={"X-User": username}, params=params)

    return get
