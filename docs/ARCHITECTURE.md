# KAgent Architecture

## 1. Architectural style

KAgent uses a modular monorepo with clear boundaries between clients, control-plane services, execution workers and shared contracts.

The system starts as a modular deployment suitable for one server, while all external boundaries are designed so that services can later be distributed without changing domain contracts.

## 2. Initial components

### Web

User interface for projects, tasks, execution timelines, approvals and artifacts.

### Gateway

Rust edge service responsible for:

- request admission;
- authentication boundary;
- request identifiers;
- rate limiting;
- security headers;
- routing to internal services;
- streaming event transport.

### Control Plane

TypeScript service responsible for:

- projects;
- task lifecycle;
- workflow state;
- policies;
- audit events;
- scheduling decisions;
- references to artifacts.

### Contracts

Versioned TypeScript domain contracts shared by clients and services. Wire-level schemas will later be generated from canonical JSON Schema or Protobuf definitions.

### Infrastructure

- PostgreSQL for durable relational state;
- NATS JetStream for commands and domain events;
- S3-compatible storage for immutable artifacts.

## 3. Dependency rule

Clients depend on public contracts, never on internal service implementations.

Services may depend on contracts and local infrastructure adapters. Domain modules must not import transport or database implementations directly.

## 4. State ownership

- PostgreSQL is authoritative for projects, task state, policies and audit indexes.
- NATS is a delivery mechanism, not the final source of truth.
- Object storage is authoritative for artifact bytes.
- Audit records are append-only and later protected with hash chaining.

## 5. Security baseline

- External traffic terminates at Gateway.
- Internal services are not exposed publicly by default.
- Secrets are provided through runtime configuration and never committed.
- Local Docker ports bind to loopback.
- Privileged containers are forbidden.
- Agent execution will use isolated sandboxes with explicit capability grants.

## 6. Evolution

The initial modular deployment may later split into independent services and workers. A split is allowed only when:

- the boundary has a stable contract;
- operational benefit is measured;
- state ownership is unambiguous;
- failure and retry semantics are specified.

## 7. Reasoning Engine

KAgent is capability-first rather than model-first.

Domain agents submit a reasoning request containing:

- requested capability;
- task category and complexity;
- context and tool requirements;
- privacy class;
- latency target;
- quality target;
- hard budget;
- execution mode.

The Reasoning Engine coordinates:

- Model Registry;
- provider adapters;
- Capability Registry;
- Policy Router;
- usage accounting;
- outcome telemetry;
- optional reviewer and consensus flows.

Provider SDKs must not leak into agent domain logic.

## 8. Model evaluation and routing telemetry

Model selection is learned mainly from real task execution. The platform records model configuration, task characteristics, verification evidence, attempts, latency, tokens and cost.

Dedicated comparisons are sampled and budget-limited. Normal tasks use one model unless policy, uncertainty or criticality justifies escalation.

The canonical efficiency metric is cost per successful task, not price per call.

## 9. Agent Workspace Control Plane

Release 0.9 introduces a governed workspace aggregate between tasks and the
execution plane. The Control Plane owns lifecycle, limits, session metadata and
review state. Workers own physical Git worktrees, PTY processes and Chromium
instances. The Control Plane exposes only an opaque workspaceRef, never a host
filesystem path.

The 0.9 adapter is intentionally in memory. Migration 003 defines the durable
schema; the PostgreSQL repository and worker provisioner are required in 0.10.
See ADR-0004 and AGENT_WORKSPACE_COCKPIT.md.