from fastapi.testclient import TestClient

from src.server import app, engine


client = TestClient(app)


def test_account_operator_api_requires_internal_secret(monkeypatch) -> None:
    monkeypatch.setenv("KAGENT_SERVICE_SECRET", "test-internal-secret")
    engine.registry.set_provider_pool(
        "test-provider", "http://unused", {"operator-test": "secret-not-returned"}
    )

    assert client.get("/v1/accounts").status_code == 401
    response = client.get(
        "/v1/accounts",
        headers={"x-kagent-service-secret": "test-internal-secret"},
    )
    assert response.status_code == 200
    assert "secret-not-returned" not in response.text


def test_account_operator_api_rejects_unknown_account(monkeypatch) -> None:
    monkeypatch.setenv("KAGENT_SERVICE_SECRET", "test-internal-secret")
    response = client.post(
        "/v1/accounts/missing/disable",
        headers={"x-kagent-service-secret": "test-internal-secret"},
    )
    assert response.status_code == 404
