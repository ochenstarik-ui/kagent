"""Minimal unit tests for NATS events module."""

import pytest

from services.nats.src.events import DomainEvent


def test_domain_event_default_timestamp():
    event = DomainEvent(type="test", aggregate_id="1", aggregate_type="task")
    assert event.type == "test"
    assert event.aggregate_id == "1"
    assert event.timestamp


def test_domain_event_event_id_generated():
    event = DomainEvent(type="test", aggregate_id="1", aggregate_type="task")
    assert event.event_id


def test_domain_event_data_default():
    event = DomainEvent(type="test", aggregate_id="1", aggregate_type="task")
    assert event.data == {}


@pytest.mark.asyncio
async def test_nats_client_requires_server():
    from services.nats.src.events import NatsClient

    client = NatsClient("nats://localhost:9999")
    with pytest.raises(Exception):
        await client.connect()
