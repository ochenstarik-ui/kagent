# C5 — NATS Events

## Status

READY_FOR_OWNER_MERGE_DECISION. PR remains open and was not merged.

## Delivery

- Branch: `wt/c5-nats-events`
- Final head: `51551d66d47d0419cbf4b577f16a6fa49e53f58d`
- PR: https://github.com/ochenstarik-ui/kagent/pull/8
- Final CI run: https://github.com/ochenstarik-ui/kagent/actions/runs/31364595568

## Changes

- Moved reusable event delivery to `packages/py_events`; retained a compatibility import at the old path.
- Added idempotent JetStream creation, unified stream naming, bounded reconnect, ack/nak and request/reply handling.
- Connected `services/pipeline` as a real best-effort lifecycle-event publisher. Broker failure is logged and does not fail pipeline work.
- Added unit and real-broker integration coverage with `nats:2.11-alpine` and JetStream.
- Added NATS CI evidence to `docs/capabilities.json`; generated `docs/ROADMAP.md` from the registry.
- Removed NATS from known drift.
- Aligned pipeline and orchestrator on `nats-py==2.15.0`, Apache-2.0.
- Added ADR-0022 to avoid collision with C3 ADR-0021.

## Honest baseline constraints

- The repository-wide unrestricted Ruff invocation remains red on numerous pre-existing files; C5-added event code passes focused Ruff and the repository CI Ruff policy passes.
- The complete Windows unit collection still hits the pre-existing `services.agent_runtime` import-layout error. C5 focused tests and Linux CI pass.
