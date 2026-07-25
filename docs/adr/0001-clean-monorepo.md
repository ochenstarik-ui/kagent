# ADR-0001: Clean modular monorepo

- Status: accepted
- Date: 2026-07-24

## Context

KAgent must be developed independently from legacy and third-party agent platforms, while supporting multiple clients, security-sensitive runtime components and distributed execution.

## Decision

Use one clean monorepo with these top-level boundaries:

- `apps/` for user-facing clients;
- `services/` for deployable backend services;
- `packages/` for versioned shared contracts and libraries;
- `docs/` for specifications and ADR;
- `infrastructure/` for deployment assets when they outgrow root-level Compose.

TypeScript is used for the initial Web and Control Plane. Rust is used for Gateway and later security-sensitive worker runtime.

## Consequences

- Atomic changes across contracts and consumers are possible.
- CI can validate all components together.
- Service boundaries still require explicit contracts.
- Build tooling must support both Node.js and Rust.
