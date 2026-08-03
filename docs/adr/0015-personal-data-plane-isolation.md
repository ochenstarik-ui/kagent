# ADR-0015: Personal data plane isolation

- Status: proposed
- Date: 2026-08-03

## Context

KAgent serves two purposes: autonomous software development and a personal assistant. A Personal Assistant Agent is a defined system role, and the data egress policy already marks personal email as local-only.

Architecturally, however, personal data and project data share the same memory layers, the same search index and the same Context Builder. The only separation is policy applied at the moment of an outbound provider call.

That is the wrong place for the boundary. Personal correspondence, calendars and documents would be retrievable by a development agent working on a project, and would reach a cloud provider through any path where the egress classification is imperfect. The blast radius of a single classification error is the user's private life.

## Decision

Personal data is a separate plane, isolated by construction rather than by classification.

- separate storage, separate search index and separate object storage bucket;
- separate encryption keys under the credential vault, so that project-scope credentials cannot decrypt personal material;
- the Context Builder is structurally unable to resolve personal-plane sources for development roles: the personal plane is not among their addressable sources, regardless of policy configuration;
- only the Personal Assistant Agent addresses the personal plane, and it does not receive repository write tools;
- movement from the personal plane to a project is an explicit, audited, per-item user action, never a query result;
- the default routing for the personal plane is local models; use of a cloud provider requires explicit per-category consent;
- personal-plane deletion is independent of project deletion and is honoured across cassettes, caches and checkpoints.

## Consequences

- A misclassification in the egress firewall can no longer leak personal data into a development run, because the path does not exist.
- Cross-domain convenience is lost: the assistant cannot silently enrich a work task with personal context, and the user must move items deliberately.
- Two planes mean duplicated infrastructure for search and storage.
- Retention and deletion obligations become tractable, since personal material has one home.

## Related

- ADR-0012 (context lifecycle) enforces addressable-source restrictions.
- ADR-0013 (model call cache) inherits plane isolation.
- Specification section 40.
