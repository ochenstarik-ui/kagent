"""Service-to-service authentication tests for action endpoints."""

import json as json_module
import os
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from services.agent_runtime.src import runtime as runtime_module
from services.pipeline.src import pipeline as pipeline_module

ROOT = Path(__file__).resolve().parents[2]
SERVICE_SECRET = "test-service-secret"
SERVICE_SECRET_HEADER = "x-kagent-service-secret"

async def _request(
    app: object,
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    json: dict[str, str] | None = None,
) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, headers=headers, json=json)


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [runtime_module.app, pipeline_module.app])
@pytest.mark.parametrize(
    ("path", "expected_status"),
    [("/health/live", 200), ("/health/ready", 404)],
)
async def test_health_endpoint_does_not_require_service_secret(
    app: object,
    path: str,
    expected_status: int,
) -> None:
    response = await _request(app, "GET", path)

    assert response.status_code == expected_status


@pytest.mark.asyncio
async def test_runtime_rejects_missing_service_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KAGENT_SERVICE_SECRET", SERVICE_SECRET)

    task_id = f"task-{uuid4()}"
    response = await _request(
        runtime_module.app,
        "POST",
        "/v1/contexts",
        json={"task_id": task_id, "project_id": "project-1"},
    )

    assert response.status_code == 401
    assert task_id not in runtime_module.runtime._contexts
    assert SERVICE_SECRET not in response.text


@pytest.mark.asyncio
async def test_runtime_fails_closed_when_service_secret_is_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("KAGENT_SERVICE_SECRET", raising=False)

    response = await _request(
        runtime_module.app,
        "POST",
        "/v1/contexts",
        headers={SERVICE_SECRET_HEADER: SERVICE_SECRET},
        json={"task_id": "task-unconfigured", "project_id": "project-1"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_runtime_rejects_incorrect_service_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KAGENT_SERVICE_SECRET", SERVICE_SECRET)

    task_id = f"task-{uuid4()}"
    response = await _request(
        runtime_module.app,
        "POST",
        "/v1/contexts",
        headers={SERVICE_SECRET_HEADER: "incorrect-secret"},
        json={"task_id": task_id, "project_id": "project-1"},
    )

    assert response.status_code == 401
    assert task_id not in runtime_module.runtime._contexts
    assert SERVICE_SECRET not in response.text


@pytest.mark.asyncio
async def test_runtime_accepts_matching_service_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KAGENT_SERVICE_SECRET", SERVICE_SECRET)
    task_id = f"task-{uuid4()}"

    response = await _request(
        runtime_module.app,
        "POST",
        "/v1/contexts",
        headers={SERVICE_SECRET_HEADER: SERVICE_SECRET},
        json={"task_id": task_id, "project_id": "project-1"},
    )

    assert response.status_code == 200
    assert response.json()["task_id"] == task_id


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("headers", "expected_status"),
    [
        (None, 401),
        ({SERVICE_SECRET_HEADER: "incorrect-secret"}, 401),
        ({SERVICE_SECRET_HEADER: SERVICE_SECRET}, 200),
    ],
)
async def test_pipeline_requires_matching_service_secret(
    monkeypatch: pytest.MonkeyPatch,
    headers: dict[str, str] | None,
    expected_status: int,
) -> None:
    monkeypatch.setenv("KAGENT_SERVICE_SECRET", SERVICE_SECRET)

    response = await _request(
        pipeline_module.app,
        "GET",
        "/v1/pipelines",
        headers=headers,
    )

    assert response.status_code == expected_status
    assert SERVICE_SECRET not in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("headers", "expected_status", "expected_calls"),
    [
        (None, 401, []),
        ({SERVICE_SECRET_HEADER: "incorrect-secret"}, 401, []),
        (
            {SERVICE_SECRET_HEADER: SERVICE_SECRET},
            200,
            [("task-1", "project-1", "feature")],
        ),
    ],
)
async def test_pipeline_action_requires_matching_service_secret_before_execution(
    monkeypatch: pytest.MonkeyPatch,
    headers: dict[str, str] | None,
    expected_status: int,
    expected_calls: list[tuple[str, str, str]],
) -> None:
    calls: list[tuple[str, str, str]] = []

    async def execute(task_id: str, project_id: str, task_type: str) -> None:
        calls.append((task_id, project_id, task_type))

    monkeypatch.setenv("KAGENT_SERVICE_SECRET", SERVICE_SECRET)
    monkeypatch.setattr(pipeline_module.engine, "execute", execute)

    response = await _request(
        pipeline_module.app,
        "POST",
        "/v1/pipelines/execute",
        headers=headers,
        json={"task_id": "task-1", "project_id": "project-1"},
    )

    assert response.status_code == expected_status
    assert calls == expected_calls


@pytest.mark.asyncio
async def test_pipeline_signs_runtime_requests_with_service_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_headers: dict[str, str] = {}

    class FakeResponse:
        status_code = 200
        text = ""

        def json(self) -> dict[str, object]:
            return {}

    class FakeAsyncClient:
        def __init__(self, timeout: float) -> None:
            assert timeout == 120.0
            self.headers = captured_headers

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, url: str, json: dict[str, object]) -> FakeResponse:
            del url, json
            return FakeResponse()

    async def discard_event(subject: str, event: object) -> None:
        del subject, event

    monkeypatch.setenv("KAGENT_SERVICE_SECRET", SERVICE_SECRET)
    monkeypatch.setattr(pipeline_module.httpx, "AsyncClient", FakeAsyncClient)
    engine = pipeline_module.PipelineEngine(event_publisher=discard_event)
    engine.planner.plan = lambda task_type: []

    await engine.execute("task-1", "project-1")

    assert captured_headers[SERVICE_SECRET_HEADER] == SERVICE_SECRET


def _load_compose_config() -> tuple[dict[str, object], str]:
    if shutil.which("docker"):
        compose_env = os.environ.copy()
        compose_env["KAGENT_SERVICE_SECRET"] = SERVICE_SECRET
        completed = subprocess.run(
            ["docker", "compose", "config", "--format", "json"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            env=compose_env,
        )
        return json_module.loads(completed.stdout), SERVICE_SECRET

    import yaml

    config = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    return config, "${KAGENT_SERVICE_SECRET:-}"


def test_compose_loader_injects_service_secret_for_rendering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_env: dict[str, str] = {}

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        del kwargs["cwd"], kwargs["check"], kwargs["capture_output"], kwargs["text"]
        captured_env.update(kwargs["env"])
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json_module.dumps({"services": {}}),
            stderr="",
        )

    monkeypatch.setattr(shutil, "which", lambda command: f"/usr/bin/{command}")
    monkeypatch.setattr(subprocess, "run", fake_run)

    config, expected_service_secret = _load_compose_config()

    assert config == {"services": {}}
    assert expected_service_secret == SERVICE_SECRET
    assert captured_env["KAGENT_SERVICE_SECRET"] == SERVICE_SECRET


def _port_is_loopback(port: object) -> bool:
    if isinstance(port, str):
        return port.startswith("127.0.0.1:")
    if isinstance(port, dict):
        return port.get("host_ip") == "127.0.0.1"
    return False


@pytest.mark.parametrize(
    ("port", "expected"),
    [
        ("127.0.0.1:5432:5432", True),
        ({"host_ip": "127.0.0.1", "published": "5432", "target": 5432}, True),
        ({"host_ip": "0.0.0.0", "published": "5432", "target": 5432}, False),
    ],
)
def test_loopback_port_detection_supports_compose_formats(
    port: object,
    expected: bool,
) -> None:
    assert _port_is_loopback(port) is expected


def test_compose_does_not_publish_internal_service_ports() -> None:
    config, expected_service_secret = _load_compose_config()
    services = config["services"]

    for service_name in (
        "control-plane",
        "reasoning-engine",
        "agent-runtime",
        "pipeline",
        "observability",
    ):
        assert "ports" not in services[service_name]

    for service_name in ("postgres", "nats", "minio"):
        ports = services[service_name]["ports"]
        assert all(_port_is_loopback(port) for port in ports)

    assert services["gateway"]["ports"]
    for service_name in ("gateway", "agent-runtime", "pipeline"):
        assert (
            services[service_name]["environment"]["KAGENT_SERVICE_SECRET"]
            == expected_service_secret
        )
