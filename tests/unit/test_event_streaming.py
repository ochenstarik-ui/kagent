"""Unit tests for the shared NATS event library."""

import asyncio
import json

import pytest
from nats.js.errors import BadRequestError, NotFoundError

from packages.py_events import events as event_module
from packages.py_events.events import DomainEvent, NatsClient, stream_definition


def test_domain_event_serializes_versioned_envelope() -> None:
    event = DomainEvent(
        type="task.started",
        aggregate_id="task-1",
        aggregate_type="task",
        project_id="project-1",
        task_id="task-1",
        correlation_id="correlation-1",
        data={"taskType": "feature"},
        event_id="event-1",
        timestamp="2026-08-10T12:00:00+00:00",
    )

    assert json.loads(event.to_json()) == {
        "id": "event-1",
        "type": "task.started",
        "schemaVersion": 1,
        "occurredAt": "2026-08-10T12:00:00+00:00",
        "projectId": "project-1",
        "taskId": "task-1",
        "correlationId": "correlation-1",
        "payload": {"taskType": "feature"},
    }


def test_stream_definition_uses_subject_prefix() -> None:
    publish_definition = stream_definition("task.started")
    subscribe_definition = stream_definition("task.*")

    assert publish_definition == subscribe_definition
    assert publish_definition.name == "KAGENT_TASK"
    assert publish_definition.subjects == ("task.>",)


@pytest.mark.asyncio
async def test_connect_limits_broker_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    options: dict[str, object] = {}

    async def fake_connect(server: str, **kwargs: object) -> object:
        options["server"] = server
        options.update(kwargs)
        raise OSError("broker unavailable")

    monkeypatch.setattr(event_module.nats, "connect", fake_connect)

    with pytest.raises(OSError, match="broker unavailable"):
        await NatsClient("nats://broker:4222").connect()

    assert options == {
        "server": "nats://broker:4222",
        "connect_timeout": 2,
        "reconnect_time_wait": 1,
        "max_reconnect_attempts": 3,
    }


@pytest.mark.asyncio
async def test_publish_creates_missing_stream_before_message() -> None:
    calls: list[tuple[object, ...]] = []

    class FakeJetStream:
        async def stream_info(self, name: str) -> None:
            calls.append(("stream_info", name))
            raise NotFoundError()

        async def add_stream(self, *, name: str, subjects: list[str]) -> None:
            calls.append(("add_stream", name, subjects))

        async def publish(self, subject: str, payload: bytes) -> None:
            calls.append(("publish", subject, json.loads(payload)))

    client = NatsClient()
    client._js = FakeJetStream()
    event = DomainEvent(
        type="task.started",
        aggregate_id="task-1",
        aggregate_type="task",
        project_id="project-1",
        task_id="task-1",
        correlation_id="correlation-1",
    )

    await client.publish("task.started", event)

    assert calls[:2] == [
        ("stream_info", "KAGENT_TASK"),
        ("add_stream", "KAGENT_TASK", ["task.>"]),
    ]
    assert calls[2][0:2] == ("publish", "task.started")


@pytest.mark.asyncio
async def test_stream_creation_race_reuses_winner() -> None:
    calls: list[tuple[object, ...]] = []
    lookup_count = 0

    class FakeJetStream:
        async def stream_info(self, name: str) -> None:
            nonlocal lookup_count
            lookup_count += 1
            calls.append(("stream_info", name))
            if lookup_count == 1:
                raise NotFoundError()

        async def add_stream(self, *, name: str, subjects: list[str]) -> None:
            calls.append(("add_stream", name, subjects))
            raise BadRequestError()

    client = NatsClient()
    client._js = FakeJetStream()

    definition = await client.ensure_stream("task.started")

    assert definition.name == "KAGENT_TASK"
    assert calls == [
        ("stream_info", "KAGENT_TASK"),
        ("add_stream", "KAGENT_TASK", ["task.>"]),
        ("stream_info", "KAGENT_TASK"),
    ]


@pytest.mark.asyncio
async def test_subscribe_uses_same_stream_definition_as_publish() -> None:
    calls: list[tuple[object, ...]] = []

    class FakeSubscription:
        async def fetch(self, count: int, timeout: float) -> list[object]:
            raise asyncio.CancelledError

    class FakeJetStream:
        async def stream_info(self, name: str) -> None:
            calls.append(("stream_info", name))

        async def pull_subscribe(
            self,
            *,
            subject: str,
            durable: str,
            stream: str,
            config: object,
        ) -> FakeSubscription:
            calls.append(("pull_subscribe", subject, durable, stream))
            return FakeSubscription()

    async def handler(event: DomainEvent) -> None:
        del event

    client = NatsClient()
    client._js = FakeJetStream()

    await client.subscribe("task.*", "pipeline-test", handler)
    await asyncio.sleep(0)

    assert calls == [
        ("stream_info", "KAGENT_TASK"),
        ("pull_subscribe", "task.*", "pipeline-test", "KAGENT_TASK"),
    ]


@pytest.mark.asyncio
async def test_request_returns_decoded_response() -> None:
    class Response:
        data = b'{"status":"ok"}'

    class FakeConnection:
        async def request(self, subject: str, payload: bytes, timeout: float) -> Response:
            assert subject == "pipeline.status"
            assert json.loads(payload) == {"taskId": "task-1"}
            assert timeout == 2.0
            return Response()

    client = NatsClient()
    client._nc = FakeConnection()

    response = await client.request(
        "pipeline.status",
        {"taskId": "task-1"},
        timeout=2.0,
    )

    assert response == {"status": "ok"}
