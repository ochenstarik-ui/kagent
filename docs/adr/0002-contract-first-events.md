# ADR-0002: Contract-first commands and events

- Status: accepted
- Date: 2026-07-24

## Context

Clients, services and workers must evolve independently without relying on hidden implementation details.

## Decision

All cross-boundary commands, events and artifacts use versioned contracts.

Every event includes:

- unique event ID;
- event type;
- schema version;
- occurrence timestamp;
- project and task scope when applicable;
- correlation and causation identifiers;
- typed payload.

Breaking changes require a new schema version.

## Consequences

- Replay and audit become feasible.
- Compatibility can be tested.
- Contract governance is required from the first release.
