"""Shared domain event contract for Python services."""

import asyncio
import contextlib
import json
import re
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import nats
from nats.js import JetStreamContext
from nats.js.api import ConsumerConfig, DeliverPolicy
from nats.js.errors import BadRequestError, NotFoundError


@dataclass(frozen=True)
class StreamDefinition:
    name: str
    subjects: tuple[str, ...]


def stream_definition(subject: str) -> StreamDefinition:
    """Derive one JetStream definition for every subject under a root prefix."""
    prefix = subject.split(".", maxsplit=1)[0].strip()
    if not prefix or not re.fullmatch(r"[A-Za-z0-9_-]+", prefix):
        raise ValueError(f"Invalid NATS subject prefix: {subject!r}")
    stream_token = re.sub(r"[^A-Za-z0-9_-]", "_", prefix).upper()
    return StreamDefinition(
        name=f"KAGENT_{stream_token}",
        subjects=(f"{prefix}.>",),
    )


@dataclass
class DomainEvent:
    """Backward-compatible Python representation of the v1 event envelope."""

    type: str
    aggregate_id: str
    aggregate_type: str
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_id: str = ""
    schema_version: int = 1
    project_id: str = ""
    task_id: str = ""
    correlation_id: str = ""
    causation_id: str | None = None

    def __post_init__(self) -> None:
        if not self.event_id:
            self.event_id = str(uuid.uuid4())

    def to_json(self) -> bytes:
        envelope: dict[str, Any] = {
            "id": self.event_id,
            "type": self.type,
            "schemaVersion": self.schema_version,
            "occurredAt": self.timestamp,
            "projectId": self.project_id,
            "taskId": self.task_id,
            "correlationId": self.correlation_id,
            "payload": self.data,
        }
        if self.causation_id is not None:
            envelope["causationId"] = self.causation_id
        return json.dumps(envelope, separators=(",", ":")).encode()

    @classmethod
    def from_json(cls, payload: bytes) -> "DomainEvent":
        envelope = json.loads(payload)
        return cls(
            type=envelope["type"],
            aggregate_id=envelope.get("taskId", ""),
            aggregate_type="task",
            data=envelope.get("payload", {}),
            timestamp=envelope["occurredAt"],
            event_id=envelope["id"],
            schema_version=envelope["schemaVersion"],
            project_id=envelope.get("projectId", ""),
            task_id=envelope.get("taskId", ""),
            correlation_id=envelope["correlationId"],
            causation_id=envelope.get("causationId"),
        )


class NatsClient:
    def __init__(self, server: str = "nats://localhost:4222") -> None:
        self.server = server
        self._nc: nats.NATS | None = None
        self._js: JetStreamContext | None = None
        self._subscriptions: dict[str, asyncio.Task[None]] = {}

    @property
    def connected(self) -> bool:
        return self._nc is not None and self._js is not None

    async def connect(self) -> None:
        self._nc = await nats.connect(
            self.server,
            connect_timeout=2,
            reconnect_time_wait=1,
            max_reconnect_attempts=3,
        )
        self._js = self._nc.jetstream()

    async def close(self) -> None:
        tasks = list(self._subscriptions.values())
        for task in tasks:
            task.cancel()
        for task in tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._subscriptions.clear()
        if self._nc is not None:
            await self._nc.drain()
        self._nc = None
        self._js = None

    async def ensure_stream(self, subject: str) -> StreamDefinition:
        if self._js is None:
            raise RuntimeError("NATS not connected")
        definition = stream_definition(subject)
        try:
            await self._js.stream_info(definition.name)
        except NotFoundError:
            try:
                await self._js.add_stream(
                    name=definition.name,
                    subjects=list(definition.subjects),
                )
            except BadRequestError:
                await self._js.stream_info(definition.name)
        return definition

    async def publish(self, subject: str, event: DomainEvent) -> None:
        if self._js is None:
            raise RuntimeError("NATS not connected")
        await self.ensure_stream(subject)
        await self._js.publish(subject, event.to_json())

    async def subscribe(
        self,
        subject: str,
        durable_name: str,
        handler: Callable[[DomainEvent], Awaitable[None]],
    ) -> None:
        if self._js is None:
            raise RuntimeError("NATS not connected")
        definition = await self.ensure_stream(subject)
        subscription = await self._js.pull_subscribe(
            subject=subject,
            durable=durable_name,
            stream=definition.name,
            config=ConsumerConfig(
                deliver_policy=DeliverPolicy.ALL,
                ack_wait=30,
                max_deliver=5,
            ),
        )

        async def listen() -> None:
            while True:
                try:
                    messages = await subscription.fetch(1, timeout=10)
                    for message in messages:
                        try:
                            await handler(DomainEvent.from_json(message.data))
                            await message.ack()
                        except Exception:
                            await message.nak()
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    await asyncio.sleep(1)

        self._subscriptions[subject] = asyncio.create_task(listen())

    async def request(
        self,
        subject: str,
        payload: dict[str, Any],
        timeout: float = 10.0,
    ) -> dict[str, Any] | None:
        if self._nc is None:
            raise RuntimeError("NATS not connected")
        try:
            response = await self._nc.request(
                subject,
                json.dumps(payload).encode(),
                timeout=timeout,
            )
            return json.loads(response.data)
        except Exception:
            return None
