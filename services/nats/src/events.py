"""Compatibility import for the shared Python event library."""

from packages.py_events.events import (
    DomainEvent,
    NatsClient,
    StreamDefinition,
    stream_definition,
)

__all__ = ["DomainEvent", "NatsClient", "StreamDefinition", "stream_definition"]