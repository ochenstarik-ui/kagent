"""Run the E8 Docker Compose deployment smoke without external dependencies."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
EVIDENCE_DIR = ROOT / "deployment-evidence"
MIGRATION_PROBE = ROOT / "migrations" / "999_e8_nonempty_volume_probe.sql"
INTERNAL_SERVICE_PORTS = {
    "control-plane": 8100,
    "reasoning-engine": 8200,
    "agent-runtime": 8300,
    "pipeline": 8400,
    "observability": 8500,
}


def run(command: list[str], *, capture: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a command from the repository root and fail with bounded diagnostics."""
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        stdout = (result.stdout or "")[-2000:]
        stderr = (result.stderr or "")[-2000:]
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"stdout:\n{stdout}\nstderr:\n{stderr}"
        )
    return result


def prepare_env() -> None:
    """Create an ephemeral Compose environment with generated test credentials."""
    template = (ROOT / ".env.example").read_text(encoding="utf-8")
    replacements = {
        "POSTGRES_PASSWORD": secrets.token_hex(24),
        "JWT_SECRET": secrets.token_hex(32),
        "KAGENT_SERVICE_SECRET": secrets.token_hex(32),
        "S3_SECRET_KEY": secrets.token_hex(24),
        "GATEWAY_PORT": "8080",
    }
    output: list[str] = []
    seen: set[str] = set()
    for line in template.splitlines():
        key = line.split("=", 1)[0] if "=" in line else ""
        if key in replacements:
            output.append(f"{key}={replacements[key]}")
            seen.add(key)
        else:
            output.append(line)
    output.extend(f"{key}={value}" for key, value in replacements.items() if key not in seen)
    ENV_PATH.write_text("\n".join(output) + "\n", encoding="utf-8")


def compose_config() -> dict[str, Any]:
    raw = run(["docker", "compose", "config", "--format", "json"]).stdout
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise TypeError("docker compose config must be a JSON object")
    return parsed


def validate_internal_service_ports(config: dict[str, object]) -> None:
    """Reject any host publication for internal KAgent application services."""
    services = config.get("services")
    if not isinstance(services, dict):
        raise ValueError("Compose configuration has no services object")
    for service in INTERNAL_SERVICE_PORTS:
        definition = services.get(service)
        if not isinstance(definition, dict):
            raise ValueError(f"Compose configuration is missing service {service}")
        if definition.get("ports"):
            raise ValueError(f"internal service {service} publishes a host port")


def _parse_compose_ps(raw: str) -> list[dict[str, Any]]:
    text = raw.strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return [parsed]
        if isinstance(parsed, list) and all(isinstance(item, dict) for item in parsed):
            return parsed
    except json.JSONDecodeError:
        pass
    records: list[dict[str, Any]] = []
    for line in text.splitlines():
        item = json.loads(line)
        if not isinstance(item, dict):
            raise TypeError("docker compose ps emitted a non-object record")
        records.append(item)
    return records


def wait_for_services(
    config: dict[str, Any],
    *,
    only: set[str] | None = None,
    timeout_seconds: float = 300.0,
) -> None:
    """Wait for declared healthchecks; require running state when none exists."""
    services = config.get("services")
    if not isinstance(services, dict):
        raise ValueError("Compose configuration has no services object")
    expected = set(services) if only is None else only
    deadline = time.monotonic() + timeout_seconds
    latest: list[dict[str, Any]] = []
    while time.monotonic() < deadline:
        latest = _parse_compose_ps(
            run(["docker", "compose", "ps", "--all", "--format", "json"]).stdout
        )
        by_service = {
            str(item.get("Service")): item
            for item in latest
            if item.get("Service") is not None
        }
        ready = True
        for name in expected:
            item = by_service.get(name)
            definition = services.get(name)
            if item is None or not isinstance(definition, dict):
                ready = False
                break
            if str(item.get("State", "")).lower() != "running":
                ready = False
                break
            if definition.get("healthcheck") and str(item.get("Health", "")).lower() != "healthy":
                ready = False
                break
        if ready:
            return
        time.sleep(2)
    raise TimeoutError(
        "Compose services did not become ready before timeout:\n"
        + json.dumps(latest, indent=2, sort_keys=True)
    )


def _request(
    base_url: str,
    method: str,
    path: str,
    *,
    payload: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
    expected_status: int = 200,
) -> tuple[dict[str, Any] | list[Any] | str, dict[str, str]]:
    body = json.dumps(payload).encode() if payload is not None else None
    request_headers = {"accept": "application/json", **(headers or {})}
    if body is not None:
        request_headers["content-type"] = "application/json"
    request = urllib.request.Request(
        f"{base_url}{path}", data=body, headers=request_headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            status = response.status
            raw = response.read().decode("utf-8", errors="replace")
            response_headers = {key.lower(): value for key, value in response.headers.items()}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} returned {exc.code}: {raw[:500]}") from exc
    if status != expected_status:
        raise RuntimeError(f"{method} {path} returned {status}, expected {expected_status}")
    try:
        parsed: dict[str, Any] | list[Any] | str = json.loads(raw)
    except json.JSONDecodeError:
        parsed = raw
    return parsed, response_headers


def run_gateway_scenario(base_url: str) -> dict[str, str]:
    health, _ = _request(base_url, "GET", "/health/live")
    if not isinstance(health, dict) or health.get("status") != "ok":
        raise AssertionError("Gateway live health response is invalid")

    run_id = os.getenv("GITHUB_RUN_ID", "local")
    email = f"e8-{run_id}-{secrets.token_hex(4)}@example.invalid"
    password = f"E8-{secrets.token_hex(12)}"
    register, _ = _request(
        base_url,
        "POST",
        "/api/control-plane/v1/auth/register",
        payload={"email": email, "password": password},
        expected_status=201,
    )
    if not isinstance(register, dict) or not isinstance(register.get("account"), dict):
        raise AssertionError("registration response has no account")

    login, _ = _request(
        base_url,
        "POST",
        "/api/control-plane/v1/auth/login",
        payload={"email": email, "password": password},
    )
    if not isinstance(login, dict) or not isinstance(login.get("tokens"), dict):
        raise AssertionError("login response has no tokens")
    tokens = login["tokens"]
    access_token = tokens.get("accessToken")
    refresh_token = tokens.get("refreshToken")
    if not isinstance(access_token, str) or not access_token:
        raise AssertionError("login response has no access token")
    if not isinstance(refresh_token, str) or not refresh_token:
        raise AssertionError("login response has no refresh token")
    account = login.get("account")
    if not isinstance(account, dict) or not isinstance(account.get("id"), str):
        raise AssertionError("login response has no account id")
    actor_id = account["id"]
    auth_headers = {"authorization": f"Bearer {access_token}", "x-actor-id": actor_id}

    project, _ = _request(
        base_url,
        "POST",
        "/api/control-plane/v1/projects",
        payload={"name": "E8 deployment smoke", "description": "Gateway-only CI scenario"},
        headers=auth_headers,
        expected_status=201,
    )
    if not isinstance(project, dict) or not isinstance(project.get("id"), str):
        raise AssertionError("project response has no id")
    project_id = project["id"]

    task, _ = _request(
        base_url,
        "POST",
        "/api/control-plane/v1/tasks",
        payload={
            "projectId": project_id,
            "title": "Verify deployment",
            "description": "Created through the public Gateway",
        },
        headers=auth_headers,
        expected_status=201,
    )
    if not isinstance(task, dict) or not isinstance(task.get("id"), str):
        raise AssertionError("task response has no id")
    task_id = task["id"]

    fetched, _ = _request(
        base_url,
        "GET",
        f"/api/control-plane/v1/tasks/{task_id}",
        headers=auth_headers,
    )
    if not isinstance(fetched, dict) or fetched.get("projectId") != project_id:
        raise AssertionError("task read-back does not match the created project")

    audit, _ = _request(
        base_url,
        "GET",
        f"/api/control-plane/v1/audit?projectId={project_id}",
        headers=auth_headers,
    )
    if not isinstance(audit, dict) or not audit.get("items"):
        raise AssertionError("audit log is empty after project and task creation")

    observability_health, _ = _request(
        base_url, "GET", "/api/observability/v1/health"
    )
    if not isinstance(observability_health, dict):
        raise AssertionError("observability health response is invalid")
    overall = observability_health.get("overall")
    services = observability_health.get("services")
    if overall not in {"healthy", "degraded"} or not isinstance(services, list):
        raise AssertionError("observability health response has no aggregate status")
    service_states: list[str] = []
    for service in services:
        if not isinstance(service, dict):
            raise AssertionError("observability health contains a non-object service")
        name = service.get("name")
        status = service.get("status")
        if not isinstance(name, str) or not isinstance(status, str):
            raise AssertionError("observability health service has no name or status")
        service_states.append(f"{name}:{status}")

    dashboard, _ = _request(base_url, "GET", "/api/observability/v1/dashboard")
    if not isinstance(dashboard, dict) or dashboard.get("title") != "KAgent Dashboard":
        raise AssertionError("observability dashboard response is invalid")

    return {
        "project_id": project_id,
        "task_id": task_id,
        "observability": overall,
        "observability_services": ",".join(service_states),
    }


def assert_host_perimeter_closed(host: str = "127.0.0.1") -> dict[str, str]:
    results: dict[str, str] = {}
    for service, port in INTERNAL_SERVICE_PORTS.items():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            if sock.connect_ex((host, port)) == 0:
                raise AssertionError(f"internal service {service} answers on host port {port}")
        results[service] = "closed"
    return results


def assert_runtime_rejects_missing_secret() -> None:
    code = (
        "import urllib.error,urllib.request; "
        "url='http://agent-runtime:8300/v1/tools'; "
        "\ntry: urllib.request.urlopen(url,timeout=5)"
        "\nexcept urllib.error.HTTPError as exc:"
        "\n assert exc.code == 401, exc.code"
        "\nelse: raise AssertionError('runtime accepted a request without service secret')"
    )
    run(["docker", "compose", "exec", "-T", "pipeline", "python", "-c", code])


def demonstrate_nonempty_volume_migration(config: dict[str, Any]) -> dict[str, str]:
    if MIGRATION_PROBE.exists():
        raise FileExistsError(f"migration probe already exists: {MIGRATION_PROBE}")
    run(["docker", "compose", "stop", "postgres"])
    MIGRATION_PROBE.write_text(
        "CREATE TABLE e8_nonempty_volume_probe (id integer primary key);\n",
        encoding="utf-8",
    )
    try:
        run(["docker", "compose", "start", "postgres"])
        wait_for_services(config, only={"postgres"}, timeout_seconds=120)
        query = (
            'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc '
            '"SELECT to_regclass(\'public.e8_nonempty_volume_probe\') IS NULL"'
        )
        result = run(["docker", "compose", "exec", "-T", "postgres", "sh", "-c", query])
        if result.stdout.strip() != "t":
            raise AssertionError(
                "new initdb migration unexpectedly ran on the existing PostgreSQL volume"
            )
        return {"existing_volume": "preserved", "new_initdb_migration": "not_applied"}
    finally:
        MIGRATION_PROBE.unlink(missing_ok=True)


def run_smoke() -> None:
    EVIDENCE_DIR.mkdir(exist_ok=True)
    config = compose_config()
    validate_internal_service_ports(config)
    wait_for_services(config)
    gateway_port = os.getenv("GATEWAY_PORT", "8080")
    scenario = run_gateway_scenario(f"http://127.0.0.1:{gateway_port}")
    perimeter = assert_host_perimeter_closed()
    assert_runtime_rejects_missing_secret()
    migration = demonstrate_nonempty_volume_migration(config)
    (EVIDENCE_DIR / "scenario.json").write_text(
        json.dumps(scenario, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (EVIDENCE_DIR / "perimeter.json").write_text(
        json.dumps(perimeter, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (EVIDENCE_DIR / "migration.json").write_text(
        json.dumps(migration, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("DEPLOYMENT SMOKE PASSED")


def main() -> int:
    parser = argparse.ArgumentParser(description="KAgent Compose deployment smoke")
    parser.add_argument("action", choices=("prepare-env", "run"))
    args = parser.parse_args()
    if args.action == "prepare-env":
        prepare_env()
    else:
        run_smoke()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
