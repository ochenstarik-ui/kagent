# Roadmap

This roadmap records only verified repository state. A checked item means code
and proportionate validation exist in this repository.

## 0.1-0.8 — Existing foundation

- [x] Contract-first monorepo foundation
- [x] Project and task lifecycle foundation
- [x] Authentication and policy foundation
- [x] Single-agent runtime foundation
- [x] Verified coding pipeline foundation
- [x] Observability and Docker Compose
- [x] Web dashboard, NATS events and multi-agent orchestrator foundation

These components still require production hardening described in the threat
model and must not be treated as a production-ready autonomous platform.

## 0.9 — Agent Workspace Cockpit Foundation

- [x] Workspace, session and diff-review contracts
- [x] Bounded workspace lifecycle with verification gate
- [x] Control Plane workspace APIs and cockpit summary
- [x] Agent concurrency and repository-relative review guards
- [x] PostgreSQL migration 003_agent_workspaces.sql
- [x] Responsive /workspaces Web route
- [x] Contract and Control Plane unit tests
- [ ] PostgreSQL-backed workspace repository
- [ ] Physical Git worktree provisioning
- [ ] PTY and Chromium processes
- [ ] CLI agent harness adapters

## 0.10 — Workspace Provisioner

- [ ] Idempotent Git worktree create/recover/cleanup
- [ ] Worker leases, heartbeats and restart recovery
- [ ] Persistent Control Plane workspace repository
- [ ] Task-contract enforcement at worker boundary
- [ ] Temporary-repository and real-PostgreSQL integration tests

## 0.11 — Agent Harness and Streaming Sessions

- [ ] Normalized harness protocol for Codex, Claude Code and OpenCode
- [ ] Policy-gated PTY sessions with restart-safe scrollback
- [ ] SSE/WebSocket event streaming
- [ ] Usage and outcome telemetry by session

## 0.12 — Browser and Review Loop

- [ ] Isolated Chromium session per workspace
- [ ] DOM element selection with bounded HTML/CSS/screenshot artifacts
- [ ] Diff comment repair workflow
- [ ] GitHub pull request integration

## 0.13 — Remote and Mobile Operations

- [ ] SSH/registered remote workers
- [ ] Approval, pause, resume and kill switch from mobile
- [ ] Notification delivery and unread state

## 1.0 — Production hardening

- [ ] gVisor or Firecracker sandbox profile
- [ ] Credential vault and mTLS service identity
- [ ] Hash-chained audit log
- [ ] Multi-tenancy isolation
- [ ] Backup/restore and rollback tests
- [ ] SBOM, signing, load tests and external security review