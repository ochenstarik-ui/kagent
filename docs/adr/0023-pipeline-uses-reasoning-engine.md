# ADR 0023: Pipeline Integration with Reasoning Engine

## Status
Accepted

## Context
The Verified Coding Pipeline needs to operate autonomously by leveraging the Reasoning Engine instead of relying entirely on static templates. It must plan execution steps, generate code during the `DEVELOP` phase, and attempt autonomous repairs during the `REPAIR` phase based on test failures, while respecting path boundaries and accounting for token costs.

## Decision
- The `Planner` uses the Reasoning Engine (`capability="planning"`) to generate a dynamic list of `PipelineStep` objects.
- If planning fails, the pipeline generates a single failed step instead of silently falling back.
- During `DEVELOP` and `REPAIR` phases, the pipeline queries the Reasoning Engine (`capability="code_generation"`) to determine the runtime tool and parameters to execute.
- A hard constraint on `allowed_paths` is enforced for file modification and execution boundaries.
- Token usage and estimated cost are accumulated per step and aggregated at the pipeline level in `PipelineResult`.
- Exhausting `max_repair_cycles` halts the pipeline and transitions the state to `HUMAN_REQUIRED`.

## Consequences
- **Positive:** Increased autonomy; capable of iterative, model-driven repair and complex task planning.
- **Negative:** Susceptible to model hallucinations or incorrectly formatted JSON responses from the Reasoning Engine.
- **Mitigation:** Fallback parsing logic and `HUMAN_REQUIRED` status to gracefully halt runaway repairs.
