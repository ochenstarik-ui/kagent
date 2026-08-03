# ADR-0011: Human decision contract

- Status: proposed
- Date: 2026-08-03

## Context

The platform defines approval-required actions and a `needs-human-decision` status. It does not define what the system does while waiting.

Unspecified behaviour includes: whether the task holds its lease and its worker, how long it waits, what happens to the accumulated context after hours or days, how the human is reached, and what occurs if nobody answers. In an autonomous system that runs unattended, waiting is a normal state, not an exception, and it must be engineered.

The practical failure is a fleet of parked tasks each pinning a worker and a stale context, with a user who was never notified.

## Decision

A request for a human decision is a typed, first-class object.

```yaml
question_id: q-1042
run_id: run-88
task_id: task-123
kind: approval | choice | clarification | conflict
urgency: low | normal | high | blocking
statement: "Merge conflict in services/auth touches a frozen test file"
options:
  - id: escalate
    effect: "Assign to human developer"
  - id: abandon
    effect: "Cancel task, keep branch"
default: null
ttl: PT12H
on_timeout: park | abort | assume_default
evidence:
  - artifact://run-88/conflict.patch
channels: [web, telegram]
```

Rules:

- asking a question releases the worker and the lease after a checkpoint; a waiting task consumes no execution capacity and no budget reservation;
- the context needed to resume is persisted as a checkpoint, not held in memory;
- `on_timeout: assume_default` is permitted only when a default is declared and the action is reversible; irreversible actions must use `park` or `abort`;
- questions are delivered over the user's configured channels and are visible in one queue across projects;
- an unanswered `blocking` question past its TTL raises an incident;
- answers are recorded in the audit log with the identity of the answering principal, and are replayable as run inputs.

## Consequences

- Autonomous runs can safely span human absence without holding cluster resources.
- The user gains a single inbox of decisions instead of per-project polling.
- Resumption requires checkpoint fidelity, which raises the quality bar for checkpointing.
- Question fatigue becomes a measurable risk; interventions per completed case is tracked as an autonomy metric.

## Related

- ADR-0008 (autonomy metrics) counts interventions.
- ADR-0012 (context lifecycle) defines what a resumed context contains.
- Specification section 38.
