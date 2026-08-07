# ADR-0009: Branching policy and merge queue

- Status: proposed
- Date: 2026-08-03

## Context

Each development task runs in an isolated worktree on its own branch, and the planner produces a dependency graph with parallel workstreams.

What happens when those branches meet is unspecified. The only statement about merging in the specification is that merge is forbidden when critical checks fail. That leaves the central question of parallel autonomous development unanswered: who integrates, in what order, and what happens when two agent-authored branches conflict.

The failure this produces is specific and severe: a branch verifies green against a stale base, is merged, and breaks the trunk — while every individual task report claims success.

## Decision

**Integration is serialized through a merge queue.** A change enters the queue after passing verification. The queue rebases the change onto the current trunk, re-runs the required checks, and merges only if they pass on the integrated result. Verification performed on a stale base never authorizes a merge.

**One task, one change set.** A task produces exactly one branch and one change set. Splitting requires new tasks with their own contracts.

**Trunk protection.** Direct pushes to the base branch, force pushes and history rewrites on shared branches are forbidden for all agent identities, including administrative ones. Bypass flags for verification hooks are forbidden.

**Conflict policy.** A conflict inside the task's `allowed_paths` may be resolved by the agent, followed by full re-verification. A conflict touching files outside `allowed_paths`, or touching frozen test files, is escalated as a human decision and does not consume repair cycles.

**Commit hygiene.** Commits are atomic and carry the task identifier, the run identifier and the resolved prompt registry versions in trailers, so that any line of trunk history maps back to a replayable run.

**Test diff separation.** The code diff and the test diff are distinguishable at review time, as required by test oracle integrity, and the queue enforces the approval policy that applies to changes of pre-existing tests.

## Consequences

- Integration throughput is bounded by the queue; with heavy parallelism, batching and speculative checks may be needed later.
- The trunk stays green by construction, which is a precondition for agents to rely on the repository as a source of truth.
- Rebasing may invalidate an otherwise finished task and force an extra verification pass; this cost is accepted.
- Dependent workstreams need explicit ordering in the planner rather than optimistic parallelism.

## Related

- ADR-0005 (test oracle integrity).
- ADR-0010 (effect ledger) covers the external effects a merge triggers.
- Specification section 36.
