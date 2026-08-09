"""Minimal unit tests for observability metrics module."""

import pytest

from services.observability.src.metrics import MetricsStore, ServiceHealth


def test_metrics_store_records_request():
    store = MetricsStore()
    store.record_request("/v1/metrics", 12.0, 200)
    metrics = store.get_metrics()
    assert metrics["requests"]["total"] == 1


def test_metrics_store_records_error():
    store = MetricsStore()
    store.record_request("/v1/metrics", 12.0, 500)
    metrics = store.get_metrics()
    assert metrics["errors"]["total"] == 1


def test_service_health_defaults():
    health = ServiceHealth("gateway", "http://localhost:8080/health/live")
    assert health.status == "unknown"


@pytest.mark.asyncio
async def test_check_health_down():
    from services.observability.src.metrics import check_health

    health = ServiceHealth("test", "http://localhost:99999/health")
    await check_health(health)
    assert health.status == "down"
