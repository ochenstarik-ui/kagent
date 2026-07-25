"""NATS JetStream integration — async event streaming for KAgent services.

v0.8: Event publication/subscription, retry policies, dead-letter queues.
"""

import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import nats
from nats.js import JetStreamContext
from nats.js.api import ConsumerConfig, DeliverPolicy


# ═══════════════════════════════════════════════════════════════════════
# Event types (domain events)
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class DomainEvent:
    type: str
    aggregate_id: str
    aggregate_type: str  # project, task, run, agent
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_id: str = ""

    def __post_init__(self):
        import uuid
        if not self.event_id:
            self.event_id = str(uuid.uuid4())


# ═══════════════════════════════════════════════════════════════════════
# NATS Client
# ═══════════════════════════════════════════════════════════════════════

class NatsClient:
    def __init__(self, server: str = "nats://localhost:4222"):
        self.server = server
        self._nc: Optional[nats.NATS] = None
        self._js: Optional[JetStreamContext] = None
        self._subscriptions: dict[str, asyncio.Task] = {}
        self._handlers: dict[str, list[Callable[[DomainEvent], Any]]] = {}

    async def connect(self):
        self._nc = await nats.connect(self.server)
        self._js = self._nc.jetstream()

    async def close(self):
        for task in self._subscriptions.values():
            task.cancel()
        if self._nc:
            await self._nc.drain()

    async def publish(self, subject: str, event: DomainEvent):
        if not self._js:
            raise RuntimeError("NATS not connected")
        payload = json.dumps({
            "type": event.type,
            "aggregate_id": event.aggregate_id,
            "aggregate_type": event.aggregate_type,
            "data": event.data,
            "metadata": event.metadata,
            "timestamp": event.timestamp,
            "event_id": event.event_id,
        }).encode()
        await self._js.publish(subject, payload)

    async def subscribe(self, subject: str, durable_name: str, handler: Callable[[DomainEvent], Any]):
        if not self._js:
            raise RuntimeError("NATS not connected")

        # Create or get stream
        stream_name = subject.replace(".", "_").replace("*", "all")

        # Subscribe with durable consumer
        sub = await self._js.pull_subscribe(
            subject=subject,
            durable=durable_name,
            stream=stream_name,
            config=ConsumerConfig(
                deliver_policy=DeliverPolicy.ALL,
                ack_wait=30,
                max_deliver=5,
            ),
        )

        async def _listen():
            while True:
                try:
                    msgs = await sub.fetch(1, timeout=10)
                    for msg in msgs:
                        try:
                            data = json.loads(msg.data)
                            event = DomainEvent(
                                type=data["type"],
                                aggregate_id=data["aggregate_id"],
                                aggregate_type=data["aggregate_type"],
                                data=data.get("data", {}),
                                metadata=data.get("metadata", {}),
                                timestamp=data.get("timestamp", ""),
                                event_id=data.get("event_id", ""),
                            )
                            await handler(event)
                            await msg.ack()
                        except Exception as e:
                            await msg.nak()
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    await asyncio.sleep(1)

        self._subscriptions[subject] = asyncio.create_task(_listen())

    async def request(self, subject: str, payload: dict, timeout: float = 10.0) -> Optional[dict]:
        if not self._nc:
            raise RuntimeError("NATS not connected")
        try:
            resp = await self._nc.request(subject, json.dumps(payload).encode(), timeout=timeout)
            return json.loads(resp.data)
        except Exception:
            return None


# ═══════════════════════════════════════════════════════════════════════
# Event bus singleton
# ═══════════════════════════════════════════════════════════════════════

_nats: Optional[NatsClient] = None

async def get_nats() -> NatsClient:
    global _nats
    if _nats is None:
        _nats = NatsClient(os.getenv("NATS_URL", "nats://localhost:4222"))
        await _nats.connect()
    return _nats

async def publish_event(subject: str, event: DomainEvent):
    nats = await get_nats()
    await nats.publish(subject, event)

async def subscribe_events(subject: str, durable: str, handler: Callable[[DomainEvent], Any]):
    nats = await get_nats()
    await nats.subscribe(subject, durable, handler)
