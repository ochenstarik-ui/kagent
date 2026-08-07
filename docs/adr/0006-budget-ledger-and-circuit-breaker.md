# ADR-0006: Two-phase budget ledger and cost circuit breaker

- Status: proposed
- Date: 2026-08-03

## Context

Task contracts define `max_model_cost`, execution modes define budget profiles, and the Runtime Supervisor detects budget overruns.

Three gaps remain.

First, a per-task limit does not bound total spend. Forty concurrent tasks can each stay within their own limit and still exhaust a monthly budget in an hour.

Second, a plain counter incremented after each call is racy. Concurrent workers read a stale total and all pass the check, so the limit is exceeded by design under parallelism — exactly the condition the platform is built for.

Third, detection is not prevention. A supervisor that observes an overrun after the money is spent does not protect anything.

## Decision

Spend is managed by a two-phase ledger in PostgreSQL.

**Reservation.** Before a step that may call a model, the estimated cost is reserved atomically against the owning budget. The step starts only if the reservation succeeds. Estimation uses the context size and the selected model profile.

**Commitment.** After the call, the actual cost is committed and the unused part of the reservation is released. Failed calls commit their real cost, which may be non-zero.

**Expiry.** Reservations carry a lease tied to the step lease. An orphaned reservation is released by the supervisor, so a lost worker cannot permanently hold budget.

**Hierarchy.** Budgets nest: organization, project, task, step. A reservation must succeed at every level. A child budget can never exceed its parent's free balance.

**Circuit breaker.** Burn rate is evaluated against the forecast for the current period. Exceeding the threshold moves the platform into a restricted state: no new task admission, running tasks are driven to their next checkpoint and parked. The restricted state is announced as an incident and requires an explicit operator action to clear.

**Global pause.** A single platform-wide switch stops admission of new steps everywhere, preserving checkpoints and leases. This is distinct from the per-task stop control and from the security read-only mode, and any of the three may be active independently.

**Child attribution.** Spend by a subagent is attributed to its parent through explicit attribution records, so that the parent's total is complete while each child's contribution remains separately visible in the session tree. A parent's budget bounds its whole subtree; a child cannot obtain budget its parent does not hold.

The ledger is append-only and is part of the audit surface: every reservation, commitment and release is attributable to a run, a step and a model configuration.

## Consequences

- Cost control becomes correct under concurrency, at the price of one synchronous database write before each model call.
- Cost estimation quality becomes operationally relevant: systematic underestimation produces frequent reservation churn, which is itself a measurable signal.
- A budget exhaustion becomes a graceful degradation with preserved state rather than an abrupt failure mid-task.
- Cost per successful task, the canonical efficiency metric, becomes directly computable from the ledger rather than reconstructed from logs.

## Related

- ADR-0013 (model call cache) reduces the committed side of the ledger.
- ADR-0008 (evaluation suite) uses ledger data for cost regression.
- Specification section 37.
