# ADR 0032: Account Pool and Model Registry Leases

## Status

Accepted

## Context

Parallel orchestrators and subagents cannot safely share one provider credential:
one throttled or exhausted account stops unrelated executions even when other
accounts are available.

## Decision

The Reasoning Engine uses named provider accounts grouped into role pools.
Every request obtains an exclusive in-memory lease, and releases it after
success, failure, or timeout. Accounts move between `available`, `throttled`,
`exhausted`, `failed`, and `disabled` states. A 429 response moves the account
out of rotation and retries through another eligible account. Exhausted pools
fail explicitly; they never silently borrow credentials from another role.

Operator endpoints may pin, disable, or reset an account, but never return or
log its secret. They require the internal service credential and are not routed
through the public Gateway. Execution telemetry records the non-secret account
identifier.

## Consequences

- parallel agents distribute requests across available quotas;
- routing is stateful and requires lease-safe concurrency;
- state is process-local in this release and is reset on service restart;
- durable shared leasing is required before horizontally scaling the Reasoning
  Engine.
