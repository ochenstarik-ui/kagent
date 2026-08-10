# ADR 0026: Git Contour and Task Contract

## Status
Proposed

## Context
The Verified Coding Pipeline needs to operate on isolated Git workspaces to prevent interfering with the user's base branch and to fulfill the requirement of atomic commits with task and run metadata. Furthermore, a strict task contract must be enforced to limit the paths the agent can modify, actions it can take, and resources (cost, tokens, repair cycles) it can consume.

## Decision
- We introduced `WorkspaceManager` to clone the target repository and create a deterministic branch `kagent/task-{task_id}` for each task execution.
- We introduced `GitManager` to verify modified paths against the `TaskContract.allowed_paths` before any commit is made.
- We introduced a minimal in-memory `EffectLedger` to ensure idempotency for external side-effects like pull request creation.
- The `PipelineEngine` integrates these components: setting up the workspace, enforcing limits, executing the steps, tearing down the workspace, and using the GitHub API to submit a pull request if successful.

## Consequences
- **Positive:** True isolation per task; strict boundaries are enforced; idempotency prevents duplicate pull requests on retry.
- **Negative:** Checking out the repository adds overhead to every execution.
- **Mitigation:** The workspace is torn down after each execution to reclaim disk space, while the task artifacts are preserved in a separate long-lived directory.
