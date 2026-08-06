# Architecture Decision Records

ADR files are immutable after acceptance except for status and links to superseding decisions.

Naming:

```text
NNNN-short-title.md
```

Statuses:

- proposed
- accepted
- deprecated
- superseded

## Index

| ADR | Title | Status |
|---|---|---|
| 0001 | Clean monorepo | accepted |
| 0002 | Contract-first commands and events | accepted |
| 0003 | Capability-first model routing with budget-aware evaluation | accepted |
| 0004 | Deterministic run replay via model call cassettes | proposed |
| 0005 | Test oracle integrity | proposed |
| 0006 | Two-phase budget ledger and cost circuit breaker | proposed |
| 0007 | Versioned prompt registry | proposed |
| 0008 | Platform evaluation suite and autonomy metrics | proposed |
| 0009 | Branching policy and merge queue | proposed |
| 0010 | Effect ledger for idempotent external effects | proposed |
| 0011 | Human decision contract | proposed |
| 0012 | Context lifecycle and anchors | proposed |
| 0013 | Model call cache | proposed |
| 0014 | Executable lessons as guardrails | proposed |
| 0015 | Personal data plane isolation | proposed |
| 0016 | Computed stage status and specification drift detection | proposed |
| 0017 | Programmatic execution environment as the agent tool surface | proposed |
| 0018 | Session as an append-only tree | proposed |
| 0019 | Privacy-constrained provider routing | proposed |
| 0020 | Protocol versioning and capability negotiation | proposed |

ADR-0004 through ADR-0016 are specified in sections 35–41 of `docs/KAGENT_FULL_PRODUCT_SPEC.md`.
ADR-0017 through ADR-0020 are specified in sections 42–51. They move to `accepted` when the project owner approves them.

ADR-0017 carries a blocking precondition: the programmatic execution environment is not enabled without the sandbox described in specification section 42.6. Accepting it also replaces the tool registry in the agent runtime, which is a rewrite rather than an addition.
