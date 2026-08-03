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

## 2026-08-03 — Trust, verification integrity and cost control decisions

### Context

A review of the repository against the specification found that delivery status was
self-reported and unverified: stages up to 0.8 were marked complete while continuous
integration had been failing on every push to the default branch since 0.6, project and
task persistence was not wired to PostgreSQL, and several components existed as files that
no other module imports.

That is a symptom of a structural gap rather than of individual defects. A platform that
develops itself needs mechanisms that make its own behaviour observable, its verification
non-substitutable and its spending bounded. Thirteen decisions were added to cover it.

### Accepted as proposed

- Model calls are recorded as immutable cassettes; runs are replayable without a provider.
- Role instructions live in a versioned prompt registry, never as inline literals.
- The test oracle is separated from the implementation, frozen during implementation and
  validated by mutation, so that a green status cannot be obtained by editing tests.
- Integration is serialized through a merge queue; verification on a stale base never
  authorizes a merge.
- Spend is managed by a two-phase reservation ledger with a burn-rate circuit breaker and a
  global pause; per-task limits alone do not bound total cost under parallelism.
- External effects pass through an effect ledger with idempotency keys and an outbox;
  connectors without idempotency support are restricted to read operations.
- A request for a human decision is a typed object with a TTL and a timeout policy, and it
  releases the worker and the lease while waiting.
- Context has a declared lifecycle with anchors that are never summarised and provenance
  labels that keep retrieved content as data rather than instructions.
- Model calls pass through a cache with prefix-stable context assembly and per-project
  isolation.
- A lesson becomes active only if it declares how it changes behaviour, preferably as an
  executable check.
- Personal data is a separate plane that development roles cannot address by construction.
- The platform measures itself with an evaluation suite and autonomy metrics; agents may not
  modify their own evaluation cases as part of a product task.
- Delivery status is computed from continuous integration evidence, and specification drift
  fails the build.

### Architecture artifacts

- `docs/adr/0004-deterministic-run-replay.md`
- `docs/adr/0005-test-oracle-integrity.md`
- `docs/adr/0006-budget-ledger-and-circuit-breaker.md`
- `docs/adr/0007-versioned-prompt-registry.md`
- `docs/adr/0008-platform-evaluation-suite.md`
- `docs/adr/0009-branching-and-merge-queue.md`
- `docs/adr/0010-effect-ledger.md`
- `docs/adr/0011-human-decision-contract.md`
- `docs/adr/0012-context-lifecycle.md`
- `docs/adr/0013-model-call-cache.md`
- `docs/adr/0014-executable-lessons.md`
- `docs/adr/0015-personal-data-plane-isolation.md`
- `docs/adr/0016-computed-stage-status.md`
- Specification sections 35–41.

### Next increment

Stage 0.9.0 is a precondition for everything else: restore a green trunk, wire the Control
Plane to PostgreSQL, and add a Python job to continuous integration. Nothing in 0.9.1–0.9.5
is verifiable while the build is red.

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
