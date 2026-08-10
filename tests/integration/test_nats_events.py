"""Integration proof for NATS JetStream event publication and delivery."""

import asyncio
import os
import uuid

import pytest

from packages.py_events.events import DomainEvent, NatsClient


@pytest.mark.asyncio
async def test_jetstream_publish_subscribe_and_stream_reuse() -> None:
    nats_url = os.environ["NATS_URL"]
    publisher = NatsClient(nats_url)
    subscriber = NatsClient(nats_url)
    received: list[DomainEvent] = []
    delivered = asyncio.Event()

    async def handle(event: DomainEvent) -> None:
        received.append(event)
        delivered.set()

    await publisher.connect()
    await subscriber.connect()
    try:
        publish_definition = await publisher.ensure_stream("task.started")
        subscribe_definition = await subscriber.ensure_stream("task.*")
        assert publish_definition == subscribe_definition

        await subscriber.subscribe(
            "task.*",
            f"pipeline-integration-{uuid.uuid4().hex}",
            handle,
        )
        event = DomainEvent(
            type="task.started",
            aggregate_id="task-integration",
            aggregate_type="task",
            project_id="project-integration",
            task_id="task-integration",
            correlation_id="correlation-integration",
            data={"taskType": "feature"},
        )

        await publisher.publish("task.started", event)
        await asyncio.wait_for(delivered.wait(), timeout=10)

        assert len(received) == 1
        assert received[0].event_id == event.event_id
        assert received[0].type == "task.started"
        assert received[0].project_id == "project-integration"
        assert received[0].task_id == "task-integration"
        assert received[0].correlation_id == "correlation-integration"
        assert received[0].data == {"taskType": "feature"}
    finally:
        await subscriber.close()
        await publisher.close()
