"""Static regression guards for the build-only service image CI gate."""

import json
import re
from pathlib import Path

from scripts import drift_check


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_IMAGES = {
    "agent-runtime": "services/agent_runtime/Dockerfile",
    "control-plane": "services/control-plane/Dockerfile",
    "gateway": "services/gateway/Dockerfile",
    "observability": "services/observability/Dockerfile",
    "pipeline": "services/pipeline/Dockerfile",
    "reasoning-engine": "services/reasoning-engine/Dockerfile",
    "web": "apps/web/Dockerfile",
}


def _workflow() -> str:
    return (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")


def _job_block(workflow: str, job: str, next_job: str) -> str:
    match = re.search(
        rf"^  {re.escape(job)}:\n(?P<body>.*?)(?=^  {re.escape(next_job)}:)",
        workflow,
        re.MULTILINE | re.DOTALL,
    )
    assert match is not None, f"missing {job} CI job"
    return match.group("body")


def test_image_build_job_covers_exactly_compose_build_services() -> None:
    workflow = _workflow()
    job = _job_block(workflow, "image-build", "measurability")
    entries = dict(
        re.findall(
            r"- service: ([a-z-]+)\n\s+dockerfile: ([A-Za-z0-9_./-]+)", job
        )
    )

    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    compose_build_services = {
        service
        for service in EXPECTED_IMAGES
        if re.search(rf"^  {re.escape(service)}:\n\s+build:", compose, re.MULTILINE)
    }

    assert entries == EXPECTED_IMAGES
    assert compose_build_services == set(EXPECTED_IMAGES)


def test_image_build_is_build_only_and_uses_scoped_gha_layer_cache() -> None:
    job = _job_block(_workflow(), "image-build", "measurability")

    assert "docker/setup-buildx-action@v3" in job
    assert "docker/build-push-action@v6" in job
    assert "context: ." in job
    assert "file: ${{ matrix.dockerfile }}" in job
    assert "push: false" in job
    assert "load: false" in job
    assert "cache-from: type=gha,scope=${{ matrix.service }}" in job
    assert "cache-to: type=gha,mode=max,scope=${{ matrix.service }}" in job
    assert not re.search(r"\bdocker\s+(?:run|push)\b", job)


def test_all_dockerfiles_are_free_of_dummy_source_cache_builds() -> None:
    dockerfiles = [ROOT / path for path in EXPECTED_IMAGES.values()]
    dockerfiles.append(ROOT / "services" / "orchestrator" / "Dockerfile")

    violations: list[str] = []
    for dockerfile in dockerfiles:
        content = dockerfile.read_text(encoding="utf-8")
        if re.search(
            r"(?:echo|printf).*(?:fn main|def |class |function |package main)",
            content,
            re.IGNORECASE,
        ):
            violations.append(dockerfile.relative_to(ROOT).as_posix())

    assert violations == [], f"dummy source cache builds found in: {violations}"


def test_image_build_capability_points_to_ci_job_and_measurability_consumes_it() -> None:
    registry = json.loads(
        (ROOT / "docs" / "capabilities.json").read_text(encoding="utf-8")
    )
    capability = next(
        item
        for item in registry["capabilities"]
        if item["id"] == "infrastructure.images_build"
    )

    assert capability["name"] == "Service images build"
    assert capability["evidence"] == ["image_build_ci"]
    assert set(capability["artifacts"]) == {
        ".github/workflows/ci.yml",
        *EXPECTED_IMAGES.values(),
    }
    assert registry["evidence_checks"]["image_build_ci"] == {
        "type": "ci",
        "job": "image-build",
        "allow_failure": False,
    }

    workflow = _workflow()
    measurability = _job_block(workflow, "measurability", "nats-events")
    assert "image-build" in measurability.partition("if:")[0]


def test_infrastructure_changes_may_update_capability_registry(monkeypatch) -> None:
    monkeypatch.setattr(
        drift_check,
        "run_command",
        lambda command: (
            True,
            " M .github/workflows/ci.yml\n"
            " M docs/capabilities.json\n"
            " M services/gateway/Dockerfile",
        ),
    )

    assert drift_check.check_forbidden_paths() == []


def test_product_source_change_cannot_also_update_capability_registry(monkeypatch) -> None:
    monkeypatch.setattr(
        drift_check,
        "run_command",
        lambda command: (
            True,
            " M docs/capabilities.json\n M services/gateway/src/main.rs",
        ),
    )

    assert drift_check.check_forbidden_paths() == [
        "product task must not modify eval or measurability artifacts: "
        " M docs/capabilities.json"
    ]
