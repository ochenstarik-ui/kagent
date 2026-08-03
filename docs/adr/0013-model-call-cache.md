# ADR-0013: Model call cache

- Status: proposed
- Date: 2026-08-03

## Context

The canonical efficiency metric of the platform is cost per successful task. Multi-turn autonomous work resends a large, largely unchanged prefix on every turn: system instructions, the task contract, the tool catalogue and the accumulated history. Repair cycles repeat near-identical requests. Parallel agents on the same task frequently ask the same question.

Caching is not mentioned anywhere in the specification, yet it is the cheapest available reduction of the metric the platform optimises for.

## Decision

Model calls pass through a cache layer with three mechanisms.

**Stable prefix.** Context packages are assembled prefix-stable: invariant elements first, volatile elements last, so that provider-side prompt caching applies. Provider adapters declare whether they support prefix caching, and the router prefers configurations that do when the workload is prefix-heavy.

**Exact-response cache.** A keyed cache over `(model_id, model_version, prompt_registry_version, full_request_digest, sampling_parameters)` returns a stored response for an identical request. Entries record their origin so that cached usage is distinguishable from live usage in telemetry and in the budget ledger.

**Deduplication in flight.** Concurrent identical requests are collapsed into a single provider call, and the result is fanned out.

Constraints:

- caching is disabled for requests whose sampling parameters are explicitly non-deterministic and whose diversity is the point, such as consensus sampling and shadow comparisons;
- cache entries inherit the privacy class of the originating project and are never shared across projects or across privacy zones;
- cache entries carry a time to live and are invalidated by model version and prompt version changes;
- a cache hit is recorded in the run timeline; a run must never appear cheaper than it is by hiding hits.

## Consequences

- Direct reduction of provider spend on repair-heavy and long-horizon tasks.
- Reduced latency for repeated steps, improving the time-to-first-artifact metric.
- Cross-project cache isolation limits the hit rate but is non-negotiable under the data egress policy.
- Cache correctness becomes a source of subtle bugs if the key omits a behaviour-affecting field; the key must include every version stamp the platform tracks.

## Related

- ADR-0006 (budget ledger) records cached versus live cost.
- ADR-0004 (cassettes) is a separate mechanism: cassettes are an audit and replay record, the cache is a live optimisation, and they must not be conflated.
- Specification section 37.
