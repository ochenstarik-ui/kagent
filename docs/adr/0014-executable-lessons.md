# ADR-0014: Executable lessons as guardrails

- Status: proposed
- Date: 2026-08-03

## Context

Memory layers include lessons and incidents, and knowledge carries a status lifecycle from raw to active.

What is missing is the causal link from a lesson to future behaviour. Nothing specifies how a lesson reaches the context of the role that needs it, how conflicting lessons are resolved, when a lesson expires, or how anyone knows whether a lesson ever prevented anything.

Without that link, the lesson layer accumulates plausible advice that no agent reads, grows without bound, and quietly contradicts itself.

## Decision

A lesson is admitted to `active` status only if it declares how it changes behaviour. Three forms are permitted.

**Executable check.** The lesson is expressed as a verification rule that runs in the pipeline — a lint rule, a policy assertion, a forbidden pattern, an added evaluation case. This is the preferred form: it is testable and cannot be ignored.

**Contract change.** The lesson modifies a default in task contracts, tool permissions or routing policy.

**Scoped context rule.** The lesson is injected into the context of a specific role under a declared trigger condition. It must state the role, the trigger and a token cost.

Additional rules:

- a lesson without one of these forms stays `candidate` and never enters any context;
- a new lesson is checked against active lessons for contradiction; a contradiction requires resolution by supersession, not coexistence;
- lessons carry a review date; an unreviewed lesson decays to `stale` and stops being applied;
- each lesson records how many times it fired and how many times it blocked a defect, so that useless guardrails can be retired;
- lessons derived from an incident link to that incident and to the run that produced it.

## Consequences

- The memory layer becomes an active control surface rather than a document archive.
- Guardrail growth is bounded by measurable usefulness instead of by curation effort.
- Expressing lessons as executable checks pushes work toward verification, where it is durable, and away from prompt text, where it is fragile.
- Some genuine insight is not expressible as a check and will remain as scoped context rules with an explicit token cost.

## Related

- ADR-0012 (context lifecycle) accounts for the token cost of injected rules.
- ADR-0008 (evaluation suite) is where lesson-derived cases live.
- Specification section 40.
