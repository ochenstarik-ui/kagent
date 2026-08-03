# Agent Changelog

## 2026-07-24 — Foundation Bootstrap 0.1.0-dev

### Source of truth

1. `docs/KAGENT_FULL_PRODUCT_SPEC.md`
2. `docs/THREAT_MODEL.md`
3. `docs/adr/`
4. Versioned contracts in `packages/contracts/`

### Implemented

- Created clean monorepo boundaries.
- Added initial task, event and artifact contracts.
- Added Control Plane and Gateway skeletons.
- Added local development infrastructure.
- Added baseline validation scripts and CI.
- Removed the obsolete migration-first instruction from the product specification.

### Constraints

- Do not copy source files from Hermes, n8n, Obsidian Mind or other agent platforms.
- Do not add a dependency without checking its license.
- Do not place secrets in tracked files.
- Contract changes require a version bump or an explicit backward-compatible extension.
- User-facing changes must update `CHANGELOG.md`.
- Architecture or implementation decisions must update this file and, when appropriate, add an ADR.

### Next increment

Implement persistent project and task lifecycle in Control Plane:

- database migrations;
- project CRUD;
- task submission;
- append-only audit events;
- health/readiness probes;
- contract and integration tests.

## 2026-07-24 — Capability-first routing decision

### Accepted

- KAgent remains provider-neutral.
- Agents request capabilities rather than named models.
- Model quality is learned mainly from normal task outcomes.
- Full continuous benchmarking is prohibited as the default strategy.
- Shadow evaluation must be sampled and budget-limited.
- Economy, Balanced and Critical execution modes are required.
- Hard per-task limits are required for cost, tokens, calls, candidates and repair loops.
- Routing optimizes for cost per successful task.
- Objective verification has priority over LLM judging.
- Provider/model/version/configuration combinations receive separate performance profiles.

### Architecture artifact

- `docs/adr/0003-capability-first-model-routing.md`

## 2026-08-03 — Agent Workspace Cockpit 0.9.0-dev

### Implemented

- Added clean-room workspace, session and diff-review contracts.
- Added validated Control Plane lifecycle and cockpit APIs.
- Added migration 003 for durable workspace state.
- Added the `/workspaces` operational UI.
- Added lifecycle, concurrency and review-path tests.
- Reconciled package versions and the roadmap with verified scope.

### Validation

- Contracts typecheck and 7 unit tests passed.
- Control Plane TypeScript build and 6 unit tests passed.
- Web typecheck and production build passed; `/workspaces` is registered.
- Python compileall and repository validation passed.
- Rust checks were not run because Rust is unavailable in this environment.
- Real PostgreSQL integration tests were not run; the workspace API still uses
  the in-memory adapter and this limitation is explicit.

### Next increment

Implement release 0.10 Workspace Provisioner: PostgreSQL persistence, worker
leases, idempotent Git worktree provisioning, recovery and integration tests.
## 2026-08-03 — Workspace Provisioner 0.10.0-dev

Implemented persistent Control Plane repositories, canonical task contracts,
worker leases with expiry recovery, idempotent worker-owned Git worktrees,
worker-boundary validation, migration 004 and proportional tests. Local Git,
TypeScript and Python checks pass; real PostgreSQL execution is pending because
the current environment has no Docker/PostgreSQL executable.