# ADR-0020: Protocol versioning and capability negotiation

- Status: proposed
- Date: 2026-08-06

## Context

Contract-first commands and events require a new schema version for breaking changes. That rule states the obligation and leaves the operational question open: how a change is classified, how a new server behaves toward an old client, and what evidence proves compatibility.

The question is not theoretical for KAgent. Workers, satellites, desktop clients, mobile clients and the command line will run versions the control plane did not ship with, on machines the operator does not update on demand. A worker that silently stops accepting tasks after a control plane upgrade is an outage.

Prime Agent's development rules for its daemon protocol supply a workable procedure, refined here for a fleet that is genuinely remote.

## Decision

Every change to a cross-boundary command, event or response shape is classified before it is written, and the classification determines what else the change must carry.

**Classification.**

- *Backward compatible*: additive and ignorable by an older peer. No version bump.
- *Capability gated*: new behaviour available only when both peers advertise the capability. No version bump; the capability name is part of the contract.
- *Incompatible*: an older peer cannot function correctly. Requires a protocol version bump and a migration path.

**Negotiation.** Peers exchange a protocol version and a capability set on connect. A client must check for a capability before using it; a server must not assume a capability it did not receive. Unknown fields are ignored rather than rejected, and unknown capabilities are never assumed.

**Compatibility evidence.** Every wire change updates the compatibility map and adds tests in both directions: new client against old server, and old client against new server. A wire change without both tests does not merge.

**Deprecation window.** A supported version range is declared and enforced. A peer below the floor is refused with an explicit, actionable error rather than an obscure failure, and the refusal is an incident when it affects an enrolled worker.

**Scope.** The rule applies to the worker API, the client connection protocol, the infrastructure bridge, webhooks and the event envelope on the message broker.

## Consequences

- Fleet upgrades stop requiring lockstep, which is a precondition for remote workers and satellites.
- Every wire change costs two additional tests; this is cheap relative to a partial outage across an unattended fleet.
- Capability negotiation adds a small amount of state to every connection and makes conditional behaviour explicit in the code rather than implied by version comparisons.
- The compatibility map becomes a maintained artifact and a required part of review.

## Related

- ADR-0002 (contract-first commands and events) states the obligation this decision operationalises.
- Specification section 47.
