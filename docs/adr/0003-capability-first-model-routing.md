# ADR-0003: Capability-first model routing with budget-aware evaluation

- Status: accepted
- Date: 2026-07-24

## Context

KAgent must not depend on one AI provider or one model family. Different models perform differently across coding, planning, review, security analysis, tool use, multilingual work and long-context tasks.

A naive approach would continuously benchmark every model against every task category. That would consume excessive tokens, provider quotas, compute and money.

## Decision

KAgent uses a capability-first, provider-neutral reasoning architecture.

Agents request capabilities and constraints rather than a named model. A Reasoning Engine and Policy Router select one or more eligible model configurations using:

- required capabilities;
- privacy constraints;
- historical task performance;
- reliability;
- latency;
- availability;
- cost per successful task;
- task budget;
- user-selected execution mode.

The core domain must use abstract model identities and contracts. Provider-specific names and APIs remain inside adapters and the Model Registry.

## Evaluation strategy

Model capability profiles are learned primarily from normal production work.

Measurements should reuse checks already required for task completion:

- compilation;
- automated tests;
- lint and static analysis;
- security scanners;
- contract validation;
- acceptance criteria;
- repair attempts;
- latency;
- token usage;
- total cost.

Dedicated evaluation is event-driven rather than continuous. It is allowed when:

- a new model or adapter is introduced;
- a model version or configuration changes;
- observed quality degrades;
- routing confidence is low;
- the task is critical enough to justify comparison.

Shadow evaluation must use a small, configurable sample and respect a hard budget. It is disabled by default in Economy mode.

## Execution modes

### Economy

- one eligible low-cost model;
- no consensus;
- no shadow execution by default;
- escalation only after objective failure.

### Balanced

- selection by historical cost per successful task;
- limited reviewer use;
- rare budget-limited shadow sampling;
- automatic escalation when confidence is low.

### Critical

- independent candidate solutions when justified;
- independent review;
- stronger verification;
- explicit higher budget and call limits.

## Budget controls

Every task receives hard limits:

- maximum monetary cost;
- maximum input and output tokens;
- maximum model calls;
- maximum candidates;
- maximum repair attempts;
- maximum reviewer calls;
- shadow sampling allowance;
- consensus permission.

The router must stop or request approval before exceeding a hard limit.

## Ranking principle

The primary optimization target is not raw benchmark quality or cheapest single call.

KAgent optimizes for:

```text
cost_per_successful_task =
total_cost_of_all_attempts / successfully_completed_tasks
```

Historical scores are scoped by:

- provider;
- model;
- model version;
- configuration;
- capability;
- task category;
- programming language or domain;
- context size;
- tool set;
- difficulty class.

A changed model version or materially different configuration is treated as a separate executor profile.

## Objective verification priority

When evaluating outputs, KAgent uses this order of evidence:

1. executable tests and acceptance checks;
2. compilation and static analysis;
3. security and policy checks;
4. contract compliance;
5. independent review;
6. human feedback;
7. subjective model judging.

A model must never be allowed to declare its own result the winner without independent evidence.

## Consequences

- Provider lock-in is reduced.
- New models can be introduced through adapters.
- Routing improves from real project outcomes.
- Evaluation cost remains bounded.
- The system requires trustworthy usage accounting and outcome telemetry.
- Sparse data and new models require conservative defaults and confidence estimates.
