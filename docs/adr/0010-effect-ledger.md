# ADR-0010: Effect ledger for idempotent external effects

- Status: proposed
- Date: 2026-08-03

## Context

Idempotency is required in three places: workflow node requirements, the tool contract, and cluster fault tolerance. In all three it is stated as an obligation and not as a mechanism.

Retries are guaranteed to happen: leases expire, workers die, brokers redeliver, supervisors requeue orphans. Without a mechanism, a retried step that already pushed a branch, opened a pull request, sent a message, called a payment-bearing connector or triggered a deployment will do it again. The second effect is invisible to the agent, which believes it is performing the action for the first time.

An agent platform with write access to external systems and no effect deduplication is unsafe regardless of how good its sandbox is.

## Decision

All effects that leave the platform boundary are mediated by an effect ledger.

**Idempotency key.** Every external effect is identified by a deterministic key derived from `run_id`, `step_id`, effect type and a canonical digest of the effect payload. The key is computed before the effect is attempted.

**Ledger record.** The ledger stores the key, the effect type, the target system, the request digest, the state (`intended`, `in_flight`, `succeeded`, `failed`, `unknown`), the external identifier returned by the target, and timestamps. It is append-only in PostgreSQL and is part of the audit surface.

**Protocol.** A step writes `intended` before acting and transitions the record as it proceeds. On retry, an existing record for the key short-circuits: a `succeeded` record returns the stored result without re-executing; an `unknown` record blocks and raises a reconciliation incident rather than guessing.

**Outbox.** Effects derived from a committed state change are published through an outbox table in the same transaction as the state change, then dispatched. State and intent can never diverge.

**Connector obligation.** A connector that performs write operations must accept an idempotency key or expose a reliable natural key for reconciliation. Connectors that satisfy neither are restricted to read operations and may not be granted write permissions by policy.

**Reconciliation.** For each write connector, a reconciliation procedure resolves `unknown` records against the target system. Absence of a reconciliation procedure is a blocking gap for production use of that connector.

## Consequences

- Retries become safe, which in turn makes aggressive retry policies acceptable.
- The connector interface gains a hard requirement that will exclude some third-party integrations from write access until adapted.
- Duplicate side effects become detectable after the fact, because every external identifier is recorded.
- The ledger is another synchronous write on the critical path of external actions; this is accepted for correctness.

## Related

- ADR-0006 (budget ledger) uses the same reservation discipline for money.
- ADR-0009 (merge queue) is a consumer for repository effects.
- Specification section 37.
