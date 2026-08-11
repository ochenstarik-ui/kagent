# Agent Changelog

## 2026-08-12 — Tracked verified capability status

- Scheme B stores accepted `main` push evidence in `docs/ci-results.json`, making deterministic roadmap generation visibly retain verified state.
- Evidence from pull requests, non-main branches, or incomplete/mismatched provenance fails closed.
- CI publishes successful main evidence through a unique automation branch and pull request, then explicitly dispatches CI on that branch; direct main pushes, force pushes, and automatic merges remain prohibited.

## 2026-08-11 — Unprivileged Runtime Sandbox

- **Sandbox Implementation:** Agent Runtime uses `bubblewrap` to securely isolate capabilities.
- **Fail-Fast:** Execution fails if `bubblewrap` is missing; no silent degradation.
- **Isolation:** Mounts are strictly constrained to the workspace; the process runs unprivileged with no network or IPC access, and secrets are dropped from the environment.
- **Architecture Artifact:** `docs/adr/0030-unprivileged-runtime-sandbox.md`.

## 2026-08-10 — Decision review: statuses, scope and scheduling

The project owner delegated the outstanding decisions with a single instruction: make the
project work. They are recorded here so that the reasoning survives the conversation.

### Decision statuses

Reviewed as a whole; see `docs/adr/README.md` for the result. Decisions that already govern
daily work moved to `accepted`; decisions covering work not yet started stay `proposed`; the
four decisions marked accepted by their own authors are ratified rather than reverted,
because they are sound and implemented, while the rule that executors do not set that field
stands.

### ADR-0017 is deferred, not rejected

The single-tool execution surface remains the intended direction and stays `proposed`. It is
not scheduled until the product vertical is delivered and the sandbox exists. Accepting it now
would replace the tool registry that the vertical is being built on, postponing a working
product without making anything safer — the sandbox is a separate precondition either way.

### Scope decisions confirmed

The Personal Assistant Agent stays in scope; ADR-0015 depends on it. Satellite and federation
stay out of the plan until a separate specification defines ownership and conflict
resolution. Subagent recursion stays permitted to depth two, which is what makes the current
orchestration mode legal.

### Third-party code

The existing rule stands unchanged: architecture may be borrowed, source files may not.
Nothing currently under way is blocked by it, so the licence-compliance overhead of vendoring
buys nothing today.

### Order of work

Product vertical first — wire the git manager, integrate the model loop, prove it end to end
through production classes — then the runtime sandbox. Until the sandbox exists, KAgent must
not be installed on a host reachable from the internet: the runtime executes model-authored
code, and the perimeter added in ADR-0025 protects the boundary, not the inside.

### Repository hygiene

Branches whose work reached `main` were deleted. Branches holding unlanded work were kept.
The unreviewed nine-thousand-line draft opened before any of these rules existed was closed;
its branch is preserved.

## 2026-08-10 — Importable Agent Runtime package

- `services/agent_runtime` is the single canonical source and Python import path; no
  compatibility directory or import-path workaround is retained.
- Docker build inputs and capability metadata now resolve to that package.
- The required Python CI evidence includes `tests/unit/test_runtime.py`. The complete unit
  directory remains blocked independently by the removed `services.auth` package still
  imported by `tests/unit/test_totp.py`.

## 2026-08-10 — CI evidence-fed computed roadmap

- The `measurability` job runs after every evidence-producing job and consumes only the
  in-run `needs` context; it does not query GitHub APIs or require write permissions.
- Each job publishes the outcome of every canonical registry command it covers. Only a
  successful step verifies command evidence, so a failed job can preserve earlier passing
  evidence while a declared but skipped command remains unverified.
- The uploaded roadmap records the run link and commit for accepted evidence while the
  committed deterministic roadmap remains protected by the existing manual-edit guard.
- The forbidden-path drift rule now distinguishes standalone measurability work from a
  product change that attempts to modify eval or measurability artifacts in the same task.

## 2026-08-10 — Internal service perimeter

- Gateway is the only KAgent HTTP service published by the default Compose file; Control
  Plane, Reasoning Engine, Agent Runtime, Pipeline, and Observability remain reachable only
  on the internal Compose network.
- Gateway routes `/api/observability/*`, preserves upstream route/query semantics, and signs
  requests with the installation's `KAGENT_SERVICE_SECRET`; Pipeline uses the same header for
  Runtime calls.
- Agent Runtime and Pipeline reject non-health requests with `401` unless the shared secret
  matches in constant time. Health probes remain unauthenticated.
- This is a bootstrap control, not a service identity system; mTLS and scoped identities
  remain deferred.

## 2026-08-10 — TOTP second factor in Control Plane

- TOTP is implemented beside the existing TypeScript session and password flow; the dead
  standalone Python module is removed instead of introducing a network hop in login.
- Login challenges and accepted time steps are process-local because task C4 explicitly
  forbids a schema change. Horizontal scaling therefore requires sticky routing until a
  persistent challenge/replay store is approved.
- No dependency is added; HMAC-SHA1 and constant-time comparison use `node:crypto`.
## 2026-08-10 — Shared Python event delivery

### Decision

- The NATS event implementation lives in `packages/py_events`, matching the shared Python
  SDK boundary from specification section 7; `services/nats/src/events.py` remains a thin
  compatibility import for existing callers; pipeline reaches the single shared
  implementation through that import.
- `services/pipeline` is the first production importer and emits versioned lifecycle events
  as best-effort side effects. Broker failures are logged and events are dropped so pipeline
  execution remains independent from NATS availability.
- Guaranteed delivery remains deferred to the effect-ledger outbox in ADR-0010.

### Evidence

- Unit coverage verifies envelope serialization, stream reuse, bounded connection options,
  lifecycle publication and broker-failure isolation.
- CI job `nats-events` starts JetStream in a `nats:2.11-alpine` service container and proves
  publication, durable consumption and repeated stream initialization.
- Pipeline and orchestrator align on maintained `nats-py` 2.15.0 under the Apache-2.0
  license; this task does not add orchestrator event integration.

## 2026-08-10 — Reasoning Engine contract publication

### Implemented

- Exported the existing Reasoning Engine types from the public `@kagent/contracts` entry
  point as a backward-compatible contract extension.
- Added a source-level compatibility test that compares request fields and routing enum
  values with the Python Reasoning Engine declarations.
- Removed the resolved unreachable-module exception for the reasoning contract.

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

## 2026-08-06 — Runtime surface, session model and integration boundary

### Context

Two external inputs were reviewed: an owner-authored improvements document covering
workers, satellites and infrastructure integration, and Prime Agent, a publicly available
agent platform under an MIT licence whose runtime design the document partly draws on.

The improvements document was strong as product direction and weak as a plan: it created a
second source of truth alongside this specification, dropped the MVP definition, omitted a
green build as a precondition, and restated several obligations — idempotency, quality
gates, refinement evaluation — without the mechanisms that make them real. Its genuinely
new material has been merged into the specification rather than kept as a parallel
document.

Prime Agent supplied concrete mechanics that were missing here: a single model-facing
execution surface, an invariant separating the in-kernel shim from provider calls and the
agent loop, session storage as an append-only tree with navigation and forking, compaction
cut mechanics, child cost attribution, privacy expressed as routing constraints, and a
procedure for protocol compatibility. Its security posture was explicitly not adopted: it
states that its worker and kernel processes are not a security sandbox and that code runs
with the user's permissions, which is incompatible with a platform that reaches production
infrastructure.

### Accepted as proposed

- The model-facing surface is one programmatic execution environment rather than a tool
  registry, enabled only inside a mandatory sandbox, with a typed host bridge holding all
  authority and a shim that never calls providers or implements an agent loop.
- A session is an append-only tree of typed entries; context is derived by walking a path,
  navigation and forking are supported, and authority stays in PostgreSQL and object
  storage rather than in session files.
- Privacy is a hard constraint on the routing decision, with structural provider
  declarations, no silent degradation and no override flag for local-only classes.
- Every cross-boundary change is classified as compatible, capability-gated or
  incompatible, with negotiation on connect and compatibility tests in both directions.

### Decisions taken on open questions

- The Personal Assistant Agent is retained; the improvements document had dropped it, and
  the personal data plane decision depends on it.
- Satellite and federation are removed from the plan and deferred to a separate
  specification: two authoritative control planes require an ownership and conflict model
  that does not exist.
- Subagent recursion is permitted to depth two with a reserved subtree budget, relaxing the
  earlier prohibition while keeping tree ownership with the orchestrator.
- Installation by piping a downloaded script into a privileged interpreter is prohibited,
  including in documentation examples.

### Architecture artifacts

- `docs/adr/0017-programmatic-execution-environment.md`
- `docs/adr/0018-session-as-append-only-tree.md`
- `docs/adr/0019-privacy-constrained-provider-routing.md`
- `docs/adr/0020-protocol-versioning-and-capability-negotiation.md`
- Amendments to ADR-0004, ADR-0006 and ADR-0012.
- Specification sections 42–51.

### Constraints reaffirmed

Architecture may be borrowed from third-party agent platforms; source files may not.
Vendoring third-party code under a compatible licence requires a separate owner decision
and preservation of attribution notices.

### Next increment

Stage 0.9.0 remains the precondition. Within stage 0.10, the sandbox is a delivery blocker
for the execution environment and must land before it, not after.

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
