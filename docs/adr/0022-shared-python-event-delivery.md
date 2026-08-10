# ADR-0022: Shared Python event delivery

- Status: accepted
- Date: 2026-08-10

## Context

The JetStream client lived under `services/nats` even though that directory had no service
entry point, container or dependency manifest. The client also subscribed to streams that
it never created, and no production service imported it.

Pipeline lifecycle events must cross the service boundary using the versioned envelope from
ADR-0002. NATS availability must not become a precondition for completing pipeline work.

## Decision

The reusable Python implementation lives in `packages/py_events`, the shared Python SDK
boundary described by specification section 7. `services/nats/src/events.py` is retained as
a compatibility import for existing callers; pipeline reaches the single shared
implementation through that import.

The client derives stream names and subject sets from one subject-prefix rule and ensures
the stream exists before both publication and durable subscription. Connection and
reconnection attempts are bounded.

`services/pipeline` publishes `task.started`, `agent.started`, `agent.completed`,
`artifact.created` and `task.failed` as best-effort side effects. Publication failures are
logged and the pipeline continues; events may therefore be lost while the broker is
unavailable.

## Consequences

- Python services share one event envelope and JetStream implementation.
- Pipeline execution is isolated from broker outages.
- Delivery is not guaranteed until the transactional outbox required by ADR-0010 exists.
- A broker-backed CI job is required evidence for this capability.

## Dependency

Pipeline and orchestrator use `nats-py` 2.15.0 under the Apache-2.0 license. Aligning the
declared dependency does not integrate event delivery into the orchestrator.