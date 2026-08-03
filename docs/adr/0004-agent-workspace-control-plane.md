# ADR-0004: Governed agent workspaces

- Status: Accepted
- Date: 2026-08-03
- Release: 0.9.0-dev

## Context

KAgent needs the parallel workspaces, operational visibility and review loop
common to agent development environments. Directly exposing shells or copying a
third-party agent IDE would violate the product's security and independence
requirements.

## Decision

KAgent introduces AgentWorkspace as a first-class Control Plane aggregate.
Each workspace belongs to exactly one task, uses an isolated branch name, has an
opaque worker reference and carries explicit limits for runtime, changed files,
agent concurrency and network access.

Terminal, browser and agent sessions are metadata in the Control Plane. Process
ownership remains in the execution worker. Diff comments are durable review
inputs and do not grant the reviewer code-write permission.

The implementation is clean-room and does not copy Orca source code, UI assets,
names or trademarks.

## Consequences

- Workspaces can be audited and governed before physical provisioning exists.
- The UI can show one normalized cockpit across local and remote workers.
- Completion requires an explicit verification state.
- Worker APIs must later implement idempotent provisioning, leases and recovery.
- The initial in-memory adapter is not production-ready and must be replaced by
  the PostgreSQL adapter in release 0.10.
