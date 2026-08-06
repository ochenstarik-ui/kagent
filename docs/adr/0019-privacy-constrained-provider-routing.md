# ADR-0019: Privacy-constrained provider routing

- Status: proposed
- Date: 2026-08-06

## Context

The data egress policy classifies data and states where each class may go: public documentation anywhere, source code to approved providers only, personal email local only, credentials and production databases nowhere.

A classification is not an enforcement point. Between the policy and the provider sits a routing decision that currently has no place to carry the constraint, so the policy can only be checked by inspecting the request payload — precisely the check that fails silently when classification is imperfect.

Prime Agent exposes the missing knobs as ordinary routing configuration: refuse providers that retain data, require zero-data-retention, restrict or order the acceptable provider set, exclude named providers, and sort candidates by price within those constraints.

## Decision

Privacy is expressed as hard constraints on the routing decision, evaluated before a request is dispatched.

**Per-class constraint set.** Each privacy class declares: whether zero data retention is required, whether provider-side training or data collection must be refused, the allowed provider set, the excluded provider set, whether fallback to another provider is permitted, and the required residency region.

**Provider declarations.** Every provider adapter declares its retention posture, training posture, residency and certification status as structured metadata. A provider that does not declare a property is treated as failing it.

**Enforcement.** A model configuration that cannot satisfy the constraint set is not a candidate. If no candidate remains, the step fails with an explicit policy error and raises a decision request; it never degrades silently to a weaker provider.

**Fallback inheritance.** Fallback candidates inherit the constraints of the original request. A fallback is a routing decision, not an exemption.

**Recording.** The satisfied constraint set is recorded with the routing decision in the run timeline and the audit log, so that an auditor can answer where a given piece of data was permitted to go and why.

**Local-only classes.** For classes marked local-only, the router considers only locally hosted model configurations. There is no override flag; changing the class is the only way to change the destination, and that is an audited action.

## Consequences

- The data egress policy becomes testable: a negative test asserts that a request carrying a restricted class cannot reach a non-compliant provider.
- Provider onboarding gains a documentation requirement, and some providers become ineligible for most work.
- Cost optimisation operates strictly inside the privacy-feasible set, which occasionally selects a more expensive model; this is the intended ordering.
- Sensitive workloads may have no eligible provider until local models are qualified, which surfaces a real capability gap instead of hiding it.

## Related

- ADR-0015 (personal data plane) is the structural counterpart; this decision covers routing, that one covers addressability.
- ADR-0013 (model call cache) inherits the same constraints on cache scope.
- Specification section 46.
