"""Regression contract for the Gateway container healthcheck runtime."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_gateway_runtime_image_contains_compose_healthcheck_client() -> None:
    dockerfile = (ROOT / "services" / "gateway" / "Dockerfile").read_text(
        encoding="utf-8"
    )

    runtime_stage = dockerfile.split("FROM debian:bookworm-slim", 1)[1]
    assert "wget" in runtime_stage
