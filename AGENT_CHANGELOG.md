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
