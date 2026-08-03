# ADR-0004: Deterministic run replay via model call cassettes

- Status: proposed
- Date: 2026-08-03

## Context

KAgent executes long autonomous runs in which every meaningful decision is produced by a language model. Model calls are non-deterministic, billable and dependent on provider availability.

This creates three problems the platform cannot currently solve:

1. There is no regression test for agent behaviour. Changing a role prompt, a routing policy or a pipeline stage cannot be evaluated without spending money on a fresh live run, and the result is not comparable because the sampling differs.
2. Incident analysis is unfalsifiable. When an agent deletes a file, touches a forbidden path or loops, the only available evidence is a summary written by the same agent.
3. Model comparison is unfair. Shadow Mode and cost-per-successful-task measurements compare models on different inputs, because each run diverges after the first token.

The workflow replay described in the user interface section replays graph topology, not model behaviour.

## Decision

Every model call is recorded as an immutable cassette entry.

A cassette entry contains:

- `run_id`, `step_id`, `agent_role`, `attempt`;
- `prompt_hash` and the full rendered request, including system, tool definitions and messages;
- the full response, including tool calls, refusals and stop reason;
- `model_id`, provider, model profile version, prompt registry version;
- sampling parameters and seed when the provider supports it;
- token counts, latency, cost;
- the context package checksum defined by the Context Builder.

Cassettes are written to object storage as immutable objects and referenced from the run timeline and the audit log.

The runtime supports three modes, selected by configuration:

- `live` — call the provider, record a cassette;
- `replay` — resolve calls from cassettes by lookup key, never contact a provider;
- `record` — like `live`, but fails the run if a cassette already exists for the key, to protect fixtures from accidental overwrite.

The replay lookup key is `(run_id, step_id, attempt)` for exact replay and `(agent_role, prompt_hash)` for fixture-based replay. A missing cassette in `replay` mode is a hard error, never a silent fallthrough to a live call.

Secrets are excluded from cassettes by the same masking rules that apply to logs. A cassette is treated as project-confidential data and inherits the project data egress policy.

## Consequences

- Agent behaviour becomes testable: pipeline and role changes are validated against recorded fixtures in continuous integration at zero provider cost.
- Incidents become reproducible: an operator can replay the exact sequence that produced a bad action.
- Model comparison becomes valid: two models can be evaluated against identical inputs.
- Storage grows with run volume; cassettes require a retention policy and are subject to project deletion.
- Cassettes contain source code and task context, so they must never be exported outside the privacy zone of the originating project.

## Related

- ADR-0007 (prompt registry) supplies the version stamp that makes a cassette meaningful.
- ADR-0008 (evaluation suite) consumes cassettes as fixtures.
- Specification section 35.
