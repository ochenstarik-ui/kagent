# ADR-0005: Persistent worker leases and Git worktree ownership

- Status: Accepted
- Date: 2026-08-03
- Release: 0.10.0-dev

## Context

The 0.9 workspace aggregate could model lifecycle and review state but remained
in memory and did not own a physical checkout. Restart recovery needs durable
state while filesystem paths and Git credentials must remain worker-local.

## Decision

1. The Control Plane persists workspace state and immutable task contracts in
   PostgreSQL.
2. Task contracts are hashed using canonical key ordering and validated again at
   the Agent Runtime boundary.
3. Workers acquire short leases. Only the token hash is persisted; expiry permits
   takeover with a monotonically increasing generation.
4. A worker maps opaque checkout references to paths under one configured root.
5. Git mirrors are keyed by sanitized repository identity. Worktrees are created,
   recovered and removed through argument-array subprocess calls with timeouts.
6. Host paths are not returned by either Control Plane or Agent Runtime APIs.

## Consequences

A Control Plane or worker restart can recover state without trusting stale
in-memory ownership. Filesystem cleanup remains bounded. Release 0.10 does not
claim operating-system sandboxing, PTY isolation, Chromium isolation or complete
shell-command mediation; those require later hardening.
