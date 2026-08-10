"""Unit tests for service-to-service authentication middleware.

Verifies:
- Request without secret gets 401
- Request with wrong secret gets 401
- Request with correct secret succeeds
- /health/live responds without secret
- /health/ready responds without secret
- docker-compose.yml has no ports on internal services
"""

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.shared.service_auth import ServiceAuthMiddleware


def _make_app(secret: str = "test-secret-42") -> FastAPI:
    app = FastAPI()
    app.add_middleware(ServiceAuthMiddleware, secret=secret)

    @app.get("/health/live")
    def health_live():
        return {"status": "alive"}

    @app.get("/health/ready")
    def health_ready():
        return {"status": "ready"}

    @app.get("/v1/data")
    def get_data():
        return {"data": "secret-payload"}

    @app.post("/v1/execute")
    def execute():
        return {"result": "ok"}

    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(_make_app())


def test_no_secret_returns_401(client: TestClient) -> None:
    resp = client.get("/v1/data")
    assert resp.status_code == 401


def test_wrong_secret_returns_401(client: TestClient) -> None:
    resp = client.get("/v1/data", headers={"X-Service-Secret": "wrong"})
    assert resp.status_code == 401


def test_correct_secret_returns_200(client: TestClient) -> None:
    resp = client.get("/v1/data", headers={"X-Service-Secret": "test-secret-42"})
    assert resp.status_code == 200
    assert resp.json()["data"] == "secret-payload"


def test_health_live_without_secret(client: TestClient) -> None:
    resp = client.get("/health/live")
    assert resp.status_code == 200


def test_health_ready_without_secret(client: TestClient) -> None:
    resp = client.get("/health/ready")
    assert resp.status_code == 200


def test_post_without_secret_returns_401(client: TestClient) -> None:
    resp = client.post("/v1/execute")
    assert resp.status_code == 401


def test_post_with_correct_secret_returns_200(client: TestClient) -> None:
    resp = client.post("/v1/execute", headers={"X-Service-Secret": "test-secret-42"})
    assert resp.status_code == 200


def test_empty_secret_config_returns_401() -> None:
    """When SERVICE_SECRET is empty, all non-health requests get 401."""
    app = _make_app(secret="")
    c = TestClient(app)
    resp = c.get("/v1/data")
    assert resp.status_code == 401
    # Health still works
    resp = c.get("/health/live")
    assert resp.status_code == 200


def test_secret_not_in_error_response(client: TestClient) -> None:
    """The secret value must never appear in error responses."""
    resp = client.get("/v1/data", headers={"X-Service-Secret": "wrong"})
    assert "test-secret-42" not in resp.text
    assert "wrong" not in resp.text


def test_compose_no_internal_ports() -> None:
    """docker-compose.yml must not publish ports for internal services."""
    from pathlib import Path
    compose_path = Path(__file__).resolve().parents[2] / "docker-compose.yml"
    with open(compose_path) as f:
        compose = yaml.safe_load(f)

    internal_services = ["reasoning-engine", "agent-runtime", "pipeline", "observability"]
    for svc in internal_services:
        svc_config = compose.get("services", {}).get(svc, {})
        assert "ports" not in svc_config, (
            f"Internal service '{svc}' must not publish ports. "
            f"Found: {svc_config.get('ports')}"
        )

    # Gateway SHOULD have ports
    gateway = compose["services"]["gateway"]
    assert "ports" in gateway, "Gateway must publish ports"
