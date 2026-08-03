# ADR-0008: Platform evaluation suite and autonomy metrics

- Status: proposed
- Date: 2026-08-03

## Context

The specification defines an evaluation suite that qualifies models into capability levels. It does not define an evaluation of KAgent itself.

These are different questions. A model may improve while the platform degrades, because most of the outcome is determined by prompts, context assembly, tool contracts, verification policy and repair strategy. Observability requirements cover infrastructure signals — latency, queue depth, token consumption — but not the property the product exists to deliver: closing a real task without a human.

Without a platform-level measurement, every change to the pipeline is an opinion.

## Decision

KAgent maintains an evaluation suite of end-to-end tasks and a set of autonomy metrics reported per release.

**Suite composition.** A fixed set of tasks over pinned repository snapshots, each with a known acceptance check. Tasks are stratified by category — feature, bug fix, refactor, dependency upgrade, security fix — and by difficulty. Each case pins the base commit, the task contract and the acceptance criteria. Cases must be deterministic: no network access beyond recorded fixtures, no wall-clock dependence.

**Execution.** The suite runs in replay mode against cassettes for regression checks, and in live mode on a sampled subset for reality checks, under an explicit budget.

**Reported metrics.**

- autonomy rate: share of cases completed with zero human interventions;
- intervention count per completed case;
- repair cycles per completed case;
- rework rate: share of completed cases later reopened;
- escape defects per completed case;
- cost per successfully merged change;
- wall-clock time to first useful artifact;
- forbidden-path and policy violation attempts per case.

**Gating.** A release is blocked when autonomy rate or escape defects regress beyond the declared tolerance. Prompt and routing changes are promoted only through this gate.

**Honesty rule.** Evaluation cases are owned by the platform, not by the agents. An agent working on KAgent itself may not add, modify or disable evaluation cases as part of a feature task; that is a separate, human-approved change.

## Consequences

- Pipeline work becomes measurable and comparable across releases.
- The suite is a maintenance cost: cases rot as upstream repositories change, and pinning is mandatory.
- Early numbers will be poor and should be published anyway; the value is in the trend.
- The honesty rule is essential because KAgent develops itself and would otherwise be able to improve its own score by weakening its own exam.

## Related

- ADR-0004 (cassettes) supplies deterministic inputs.
- ADR-0005 (test oracle integrity) supplies the per-task analogue of the honesty rule.
- ADR-0016 (computed stage status) consumes suite results.
- Specification section 41.
