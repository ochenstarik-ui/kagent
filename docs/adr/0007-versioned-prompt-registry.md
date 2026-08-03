# ADR-0007: Versioned prompt registry

- Status: proposed
- Date: 2026-08-03

## Context

Model profiles are versioned, and routing decisions are recorded. The instructions that define agent roles are not.

A role prompt determines behaviour at least as strongly as the choice of model. If prompts live as string literals inside service code or as untracked configuration, then a one-line edit silently changes production behaviour, cannot be attributed, cannot be rolled back independently of a deployment, and makes recorded runs incomparable.

## Decision

Role instructions are a versioned artifact, governed like contracts.

Each prompt is a tracked file with a manifest:

- `prompt_id` and role;
- semantic version and content hash;
- declared inputs, that is the context package fields it expects;
- declared output contract, which must match the typed handoff contract of the role;
- compatible model capabilities;
- changelog entry and author.

Rules:

- runtime resolves prompts only through the registry, never from inline literals;
- every run records the resolved `prompt_id` and version for each step;
- a prompt change is a change to system behaviour and requires the evaluation suite to pass before promotion;
- previous versions remain resolvable so that recorded runs stay replayable;
- two versions of the same role may run side by side under an explicit experiment with a fixed traffic share and a decision deadline.

## Consequences

- Behaviour changes become attributable and revertible without redeploying services.
- Recorded cassettes remain meaningful, because the prompt version is part of the key.
- A/B evaluation of instructions becomes possible using the same machinery as model comparison.
- Prompt governance adds review overhead; the registry must not become a place where changes bypass code review.

## Related

- ADR-0004 (cassettes) records the resolved version.
- ADR-0008 (evaluation suite) gates promotion.
- Specification section 35.
