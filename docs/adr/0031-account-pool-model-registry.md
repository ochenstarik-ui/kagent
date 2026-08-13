# ADR 0031: Account Pool and Model Registry Leases

## Status
Proposed

## Context
Currently, the `ModelRegistry` in the reasoning engine holds a single set of credentials (API key and endpoint) for each provider. When multiple parallel agents (orchestrator and subagents) execute tasks simultaneously, they all route their requests through the same account. This leads to two critical issues:
1. **Rate Limiting (429s)**: A single account is quickly rate-limited, causing parallel execution to fail or throttle unnecessarily while other available accounts remain idle.
2. **Quota Exhaustion**: High-throughput agents burn through the quota of a single account rapidly, halting the entire pipeline.

A naive "active account" toggle is insufficient because switching the active account globally would just shift the bottleneck to the next account and still subject parallel requests to the same rate limit constraints.

## Decision
We will introduce an **Account Pool** model for the `ModelRegistry` with per-request **Leasing**:
1. **Pools instead of Keys**: Configuration will define named accounts (with credentials loaded from the environment) grouped into pools based on roles (e.g., `orchestrator`, `subagents`).
2. **Account State Machine**: Each account will have a state: `available`, `throttled`, `exhausted`, `failed`, or `disabled`.
3. **Leasing Mechanism**: 
   - For every request, an account is chosen from the allowed pool and temporarily "leased" (locked) for the duration of the request. 
   - Parallel requests will thus receive distinct accounts (if available).
   - Leases are released immediately after the request concludes (success, failure, or timeout).
4. **429 Handling**: If an account receives a 429 Too Many Requests response, it is marked as `throttled`. The reset time is parsed from the response headers (if provided) or defaults to a configurable delay. The request is immediately retried on the next available account in the pool.
5. **No Silent Degradation**: If a pool is completely exhausted, the request fails fast with a clear error. It does not silently fall back to another role's pool.
6. **Manual Control**: An API will be exposed to pin an account to a role, disable an account, or manually clear a throttle state.

## Consequences
- **Billing Telemetry**: The telemetry structure (`ModelExecution`) must now record the specific `account_id` used for the request to accurately track costs per account.
- **Complexity**: Routing logic becomes stateful and asynchronous (due to leasing locks).
- **Security**: Secrets (API keys) remain purely in-memory and will never cross the boundary into API responses or logs.
