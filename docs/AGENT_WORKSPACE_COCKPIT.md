# Agent Workspace Cockpit

**Release:** 0.10.0-dev
**Status:** workspace provisioner foundation implemented
**Decision sources:** ADR-0004 and ADR-0005

## Purpose

The cockpit is a governed execution boundary attached to one project and one
approved task. Release 0.10 turns the 0.9 in-memory aggregate into a persistent,
restart-aware worker workflow without exposing host filesystem paths.

## Implemented in 0.10

- PostgreSQL repositories for projects, tasks, workspaces, sessions and review
  comments; the Control Plane now wires them by default.
- Immutable task contracts with canonical SHA-256 digests, repository-relative
  path scopes, required checks and bounded resource/network policy.
- Worker leases with opaque one-time tokens, hash-only persistence, heartbeat,
  expiry, generation counters, release and expired-lease takeover.
- Idempotent worker-owned Git mirror/worktree create, recover and bounded cleanup.
- Agent Runtime contract validation before context creation and file-tool path
  enforcement.
- Migration 004 for task contracts, leases and opaque provisioning records.
- Route/unit tests plus a real temporary-Git-repository integration test.
- PostgreSQL integration coverage for schema, contract persistence and lease
  recovery in tests/integration/test_pg.py.

## Control Plane API

| Method | Route | Purpose |
|---|---|---|
| GET | /v1/workspaces | List persistent workspaces |
| POST | /v1/tasks/:taskId/workspace | Create a workspace for an approved task |
| GET | /v1/workspaces/:id/cockpit | Read the operational snapshot |
| POST | /v1/workspaces/:id/transition | Apply a validated lifecycle transition |
| POST | /v1/workspaces/:id/lease | Acquire or recover an expired worker lease |
| POST | /v1/workspaces/:id/heartbeat | Renew a matching active lease |
| POST | /v1/workspaces/:id/lease/release | Release a matching active lease |
| POST | /v1/workspaces/:id/provisioning | Persist a lease-authenticated provisioning result |
| GET/POST | /v1/workspaces/:id/sessions | List or register session metadata |
| GET/POST | /v1/workspaces/:id/review-comments | List or add diff comments |
| POST | /v1/workspaces/:id/review-comments/:commentId/resolve | Resolve a comment |

## Agent Runtime API

| Method | Route | Purpose |
|---|---|---|
| POST | /v1/workspaces/provision | Validate a task contract and create/recover a worktree |
| POST | /v1/workspaces/cleanup | Remove a bounded worker-owned worktree |
| POST | /v1/contexts | Create a contract-bound runtime context |

Runtime responses return workspaceRef and checkoutRef values, never host paths.

## Security invariants

1. Only approved or already in-progress tasks may create a workspace.
2. Task identity and canonical contract digest must match at the worker boundary.
3. Network access remains default-deny in the immutable contract.
4. Lease tokens are returned only when acquired and stored only as SHA-256 hashes.
5. A live lease cannot be stolen; an expired lease increments generation on recovery.
6. Git subprocesses use argument arrays, disabled terminal prompting and bounded timeouts.
7. Checkout cleanup resolves under the configured worker root before removal.
8. File tools reject paths outside allowedPaths or paths containing traversal.
9. Completion still requires the verifying lifecycle state.
10. PTY, Chromium and CLI harness processes remain outside this release.

## Validation status

- Control Plane and contract tests pass locally.
- Temporary Git provision/create/recover/cleanup tests pass against the installed
  Git executable.
- Python compileall passes.
- The real PostgreSQL test is implemented but was not executed in the current
  environment because Docker/PostgreSQL is unavailable.

## Next increment: 0.11

- Normalized Codex, Claude Code and OpenCode harness protocol.
- Policy-gated PTY with restart-safe scrollback.
- SSE/WebSocket session streaming.
- Usage and outcome telemetry by session.
