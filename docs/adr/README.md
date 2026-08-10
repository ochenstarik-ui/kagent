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
| 0004 | Deterministic run replay via model call cassettes | accepted |
| 0005 | Test oracle integrity | accepted |
| 0006 | Two-phase budget ledger and cost circuit breaker | proposed |
| 0007 | Versioned prompt registry | proposed |
| 0008 | Platform evaluation suite and autonomy metrics | accepted |
| 0009 | Branching policy and merge queue | accepted |
| 0010 | Effect ledger for idempotent external effects | accepted |
| 0011 | Human decision contract | proposed |
| 0012 | Context lifecycle and anchors | proposed |
| 0013 | Model call cache | proposed |
| 0014 | Executable lessons as guardrails | proposed |
| 0015 | Personal data plane isolation | proposed |
| 0016 | Computed stage status and specification drift detection | accepted |
| 0017 | Programmatic execution environment as the agent tool surface | proposed |
| 0018 | Session as an append-only tree | proposed |
| 0019 | Privacy-constrained provider routing | proposed |
| 0020 | Protocol versioning and capability negotiation | proposed |
| 0021 | Public Reasoning Engine contract | accepted |
| 0022 | Shared Python event delivery | accepted |
| 0023 | TOTP authentication in Control Plane | accepted |
| 0024 | Importable Python Agent Runtime package | accepted |
| 0025 | Internal service perimeter and shared secret | accepted |

ADR-0004 through ADR-0016 are specified in sections 35–41 of `docs/KAGENT_FULL_PRODUCT_SPEC.md`.
ADR-0017 through ADR-0020 are specified in sections 42–51.

## Status review of 2026-08-10

Statuses were reviewed as a whole, because the table had drifted into the opposite of
reality: decisions that already governed daily work were `proposed`, while four decisions had
been marked `accepted` by the executors that authored them.

**Accepted** — these decisions govern current practice and are binding now: 0004 (tests never
call a paid provider), 0005 (tests are not weakened to make a build green), 0008 and 0016
(status is computed from evidence, both wired into continuous integration), 0009 (rebase onto
trunk before merge), 0010 (git effects carry an idempotency key), 0025 (only the gateway is
published).

**Proposed** — design decisions for work not yet started: 0006, 0007, 0011, 0012, 0013, 0014,
0015, 0018, 0019, 0020. They remain binding as direction, not as current obligation.

**0021 through 0024** were marked accepted by their authors, which the rules do not permit.
The decisions themselves are sound and already implemented, so they are ratified rather than
reverted. Executors still may not set this field.

### Scheduling note for ADR-0017

ADR-0017 stays `proposed` and is **not scheduled** until the product vertical is delivered and
the runtime sandbox exists. Accepting it replaces the tool registry in the agent runtime,
which is a rewrite of the surface the vertical is currently being built on. Rewriting that
surface now would postpone a working product without making anything safer, since the sandbox
is a separate precondition either way.

It is not rejected: the reasoning in it stands, and the single-tool surface remains the
intended long-term direction.
