"""Unit tests for pipeline lifecycle event publication."""

import json

import pytest

from services.pipeline.src import pipeline as pipeline_module
from services.pipeline.src.pipeline import (
    PipelineEngine,
    PipelinePhase,
    PipelineStep,
    StepStatus,
)


@pytest.mark.asyncio
async def test_broker_failure_does_not_interrupt_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempted_events: list[tuple[str, dict[str, object]]] = []

    async def unavailable_publisher(subject: str, event: object) -> None:
        attempted_events.append((subject, json.loads(event.to_json())))
        raise OSError("broker unavailable")

    class FakeResponse:
        status_code = 200
        text = ""

        def json(self) -> dict[str, str]:
            return {"path": "artifact.txt"}

    class FakeAsyncClient:
        def __init__(self, timeout: float) -> None:
            assert timeout == 120.0

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, url: str, json: dict[str, object]) -> FakeResponse:
            del url, json
            return FakeResponse()

    monkeypatch.setattr(pipeline_module.httpx, "AsyncClient", FakeAsyncClient)
    engine = PipelineEngine(event_publisher=unavailable_publisher)
    engine.planner.plan = lambda task_type: [
        PipelineStep(PipelinePhase.DEVELOP, "Write artifact", "file_write", {})
    ]

    result = await engine.execute("task-1", "project-1")

    assert result.status is StepStatus.PASSED
    assert [subject for subject, _ in attempted_events] == [
        "task.started",
        "agent.started",
        "agent.completed",
        "artifact.created",
    ]
    for _, envelope in attempted_events:
        assert envelope["schemaVersion"] == 1
        assert envelope["projectId"] == "project-1"
        assert envelope["taskId"] == "task-1"
        assert envelope["correlationId"]


@pytest.mark.asyncio
async def test_failed_step_publishes_task_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    published_events: list[tuple[str, dict[str, object]]] = []

    async def publisher(subject: str, event: object) -> None:
        published_events.append((subject, json.loads(event.to_json())))

    class FakeResponse:
        status_code = 200
        text = ""

        def json(self) -> dict[str, object]:
            return {}

    class FakeAsyncClient:
        def __init__(self, timeout: float) -> None:
            assert timeout == 120.0

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, url: str, json: dict[str, object]) -> FakeResponse:
            del json
            if url.endswith("/v1/execute"):
                raise RuntimeError("runtime unavailable")
            return FakeResponse()

    monkeypatch.setattr(pipeline_module.httpx, "AsyncClient", FakeAsyncClient)
    engine = PipelineEngine(event_publisher=publisher)
    engine.planner.plan = lambda task_type: [
        PipelineStep(PipelinePhase.DEVELOP, "Write artifact", "file_write", {})
    ]

    result = await engine.execute("task-1", "project-1")

    assert result.status is StepStatus.FAILED
    assert [subject for subject, _ in published_events] == [
        "task.started",
        "agent.started",
        "task.failed",
    ]
    assert published_events[-1][1]["payload"] == {
        "errors": ["runtime unavailable"],
    }
