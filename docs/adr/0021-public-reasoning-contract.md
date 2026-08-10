# ADR-0021: Public Reasoning Engine contract

- Status: accepted
- Date: 2026-08-10

## Context

The existing Reasoning Engine contract in `packages/contracts/src/reasoning.ts` was not exported by `@kagent/contracts`, while the Python service declares the same request fields and routing values. Leaving the TypeScript contract private permits those declarations to drift independently, contrary to ADR-0002.

## Decision

Export the existing Reasoning Engine contract from the public `@kagent/contracts` entry point. Treat this publication as a backward-compatible additive extension, so it does not require a version bump.

Maintain a contract parity test that compares the TypeScript request fields and routing unions with the corresponding Python `DecideRequest` fields and enum values.

## Consequences

- Consumers can import the existing Reasoning Engine types from the package entry point.
- TypeScript/Python drift in the covered request fields or routing values fails the contracts test.
- The Reasoning Engine declarations and implementation remain otherwise unchanged.

## Related

- ADR-0002 (contract-first commands and events).
- ADR-0003 (capability-first model routing with budget-aware evaluation).
