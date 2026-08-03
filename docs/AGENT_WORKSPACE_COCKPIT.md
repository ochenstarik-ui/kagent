# Agent Workspace Cockpit

**Release:** 0.9.0-dev
**Status:** control-plane foundation implemented
**Decision source:** ADR-0004

## Purpose

The Agent Workspace Cockpit adds an agent-first operational layer to KAgent
without turning the platform into an unrestricted local shell. A workspace is a
governed execution boundary attached to one project and one task.

## Implemented in 0.9

- Versioned contracts for workspaces, sessions and diff review comments.
- A workspace lifecycle that requires verification before completion.
- Default-deny network policy and bounded runtime, file and concurrency limits.
- Control Plane endpoints for workspace creation, transitions, session metadata,
  line-level review comments and cockpit summaries.
- PostgreSQL migration 003_agent_workspaces.sql.
- A responsive /workspaces dashboard.
- Unit tests for lifecycle, concurrency limits and review path validation.

## API

| Method | Route | Purpose |
|---|---|---|
| GET | /v1/workspaces | List workspaces by project or task |
| POST | /v1/tasks/:taskId/workspace | Create a governed workspace record |
| GET | /v1/workspaces/:id/cockpit | Read the operational cockpit snapshot |
| POST | /v1/workspaces/:id/transition | Apply a validated lifecycle transition |
| GET/POST | /v1/workspaces/:id/sessions | List or register session metadata |
| GET/POST | /v1/workspaces/:id/review-comments | List or add diff comments |
| POST | /v1/workspaces/:id/review-comments/:commentId/resolve | Resolve a comment |

## Security invariants

1. Host filesystem paths are never returned; workspaceRef is opaque.
2. Repository URL credentials are stripped before state is returned.
3. Network access defaults to denied and may only become allowlisted.
4. An active task may have only one active workspace.
5. Agent session count cannot exceed the task contract limit.
6. Review paths must be repository-relative.
7. A running workspace cannot become completed without verification.
8. Terminal, browser and CLI execution must remain worker-owned and policy-gated.

## Explicit limitations

The 0.9 Control Plane stores runtime state in memory even though the persistent
schema is supplied. It does not yet create a physical Git worktree, PTY, browser
or CLI-agent process. The Web cockpit displays real API state but does not yet
stream worker output.

These capabilities must not be described as implemented until the 0.10 worker
provisioner and persistence adapters are complete.

## Next increment: 0.10

- PostgreSQL repository for workspace state.
- Worker lease and heartbeat protocol.
- Safe Git worktree provisioning and cleanup.
- Recovery after Control Plane or worker restart.
- Task-contract enforcement at the worker boundary.
- Integration tests using a temporary Git repository and real PostgreSQL.
