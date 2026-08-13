"""E8 contract tests for the deployment smoke and service perimeter."""

import json
from pathlib import Path

import pytest

from scripts import deployment_smoke


ROOT = Path(__file__).resolve().parents[2]
INTERNAL_SERVICES = {
    "control-plane",
    "reasoning-engine",
    "agent-runtime",
    "pipeline",
    "observability",
}


def _compose_config() -> dict[str, object]:
    return {
        "services": {
            "gateway": {"ports": [{"target": 8080, "published": "8080"}]},
            **{name: {} for name in INTERNAL_SERVICES},
        }
    }


def test_internal_service_port_guard_accepts_closed_perimeter() -> None:
    deployment_smoke.validate_internal_service_ports(_compose_config())


@pytest.mark.parametrize("service", sorted(INTERNAL_SERVICES))
def test_internal_service_port_guard_rejects_published_port(service: str) -> None:
    config = _compose_config()
    services = config["services"]
    assert isinstance(services, dict)
    services[service] = {"ports": [{"target": 8100, "published": "8100"}]}

    with pytest.raises(ValueError, match=service):
        deployment_smoke.validate_internal_service_ports(config)


def test_workflow_runs_full_deployment_smoke_and_preserves_diagnostics() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert "  deployment:" in workflow
    assert "timeout-minutes:" in workflow
    assert "python scripts/deployment_smoke.py prepare-env" in workflow
    assert "docker compose up -d --build" in workflow
    assert "python scripts/deployment_smoke.py run" in workflow
    assert "docker compose logs --no-color" in workflow
    assert "name: deployment-logs" in workflow
    assert "if: ${{ always() }}" in workflow
    assert "docker compose down -v --remove-orphans" in workflow
    assert (
        "needs: [node, rust, python, eval, image-build, deployment, nats-events, integration]"
        in workflow
    )
    assert "needs['image-build'].result == 'success'" in workflow
    assert "needs.deployment.result == 'success'" in workflow


def test_deployment_capability_requires_runtime_job() -> None:
    registry = json.loads(
        (ROOT / "docs" / "capabilities.json").read_text(encoding="utf-8")
    )
    capability = next(
        item
        for item in registry["capabilities"]
        if item["id"] == "infrastructure.docker"
    )

    assert capability["evidence"] == ["compose_syntax", "deployment_ci"]
    assert registry["evidence_checks"]["deployment_ci"] == {
        "type": "ci",
        "job": "deployment",
        "allow_failure": False,
    }


def test_gateway_scenario_records_observability_health(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[str] = []

    def fake_request(
        _base_url: str,
        method: str,
        path: str,
        **_kwargs: object,
    ) -> tuple[dict[str, object], dict[str, str]]:
        requests.append(path)
        responses: dict[str, dict[str, object]] = {
            "/health/live": {"status": "ok"},
            "/api/control-plane/v1/auth/register": {"account": {"id": "account-1"}},
            "/api/control-plane/v1/auth/login": {
                "account": {"id": "account-1"},
                "tokens": {"accessToken": "access", "refreshToken": "refresh"},
            },
            "/api/control-plane/v1/projects": {"id": "project-1"},
            "/api/control-plane/v1/tasks": {"id": "task-1"},
            "/api/control-plane/v1/tasks/task-1": {"projectId": "project-1"},
            "/api/control-plane/v1/audit?projectId=project-1": {
                "items": [{"id": "audit-1"}]
            },
            "/api/observability/v1/health": {
                "overall": "degraded",
                "services": [{"name": "gateway", "status": "down"}],
            },
            "/api/observability/v1/dashboard": {"title": "KAgent Dashboard"},
        }
        assert method in {"GET", "POST"}
        return responses[path], {}

    monkeypatch.setattr(deployment_smoke, "_request", fake_request)

    result = deployment_smoke.run_gateway_scenario("http://gateway.test")

    assert "/api/observability/v1/health" in requests
    assert result["observability"] == "degraded"
    assert result["observability_services"] == "gateway:down"


def test_deployment_docs_warn_about_nonempty_volume_migrations() -> None:
    deployment = (ROOT / "docs" / "DEPLOYMENT.md").read_text(encoding="utf-8")

    normalized = " ".join(deployment.split())
    assert "only on the first startup of an empty PostgreSQL volume" in normalized
    assert "does not apply newly added migration files" in normalized
    assert "only Gateway port 8080" in normalized
