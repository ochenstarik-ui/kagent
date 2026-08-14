# ADR 0031 – Account Pool for Provider Credentials

**Status:** Accepted  
**Date:** 2026-08-13  
**Deciders:** KAgent platform team

---

## Context

KAgent uses multiple external AI provider accounts (OpenCode-Go, NVIDIA, Codex)
for orchestrator and subagent roles. Previously each request used a single
hard-coded credential, causing:

- Single point of failure if one account hits a rate limit.
- No visibility into which accounts are throttled or exhausted.
- No operator tooling to disable/re-enable individual accounts.

## Decision

Introduce an **account pool** — a database-backed registry of provider
credentials with an LRU acquire/release cycle and explicit state machine.

### State Machine

```
          acquire          release (success)
available ───────► rented ──────────────────► available
    ▲                │                             ▲
    │                │ release (429)               │
    │                ▼                             │
    │           throttled ─── auto/manual reset ───┘
    │
    │                │ release (auth error)
    │                ▼
    │             failed ─── operator enable ──► available
    │
    └─────────── operator enable ── disabled ◄── operator disable
```

### Acquire Policy

Least-Recently-Used (LRU) selection via `ORDER BY last_used ASC NULLS FIRST`
combined with `FOR UPDATE SKIP LOCKED` to prevent concurrent requests from
receiving the same account.

### API

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/v1/account-pool` | List all accounts and states |
| `POST` | `/v1/account-pool/rent/:role` | Manually acquire for debugging |
| `POST` | `/v1/account-pool/release/:id` | Release back to pool |
| `POST` | `/v1/account-pool/disable/:id` | Remove from rotation |
| `POST` | `/v1/account-pool/enable/:id` | Re-enable |
| `POST` | `/v1/account-pool/reset-throttle/:id` | Clear throttle |

## Consequences

**Positive:**
- Requests automatically fall over to next available account on throttling.
- Operators can inspect and control each credential via API.
- LRU distribution spreads load across accounts evenly.

**Negative / Trade-offs:**
- Requires migration `006_account_pool.sql` on existing `accounts` table.
- The `accounts` table now serves dual purpose (human auth + provider creds);
  future work (ADR-tbd) should separate these concerns.

## Alternatives Considered

- **Separate `provider_accounts` table**: cleaner separation but requires
  more migration and schema work; deferred.
- **Round-robin selection**: simpler but no load-balancing awareness of
  `last_used` timing; LRU preferred.
