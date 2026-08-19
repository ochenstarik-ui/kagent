# C3 — Export Reasoning Contract

## Status

READY_FOR_OWNER_MERGE_DECISION. PR remains open and was not merged.

## Delivery

- Branch: `wt/c3-reasoning-contract`
- Commit: `853e95b45cda0c4fe33538991eacafff9ea1d13d`
- PR: https://github.com/ochenstarik-ui/kagent/pull/9
- CI run: https://github.com/ochenstarik-ui/kagent/actions/runs/31358345536

## Changes

- Published `reasoning.ts` through the `@kagent/contracts` package entry point.
- Added TypeScript/Python parity coverage for request fields and Capability, PrivacyClass, ExecutionMode and TaskCategory.
- Removed the resolved Reasoning contract entry from `docs/known-drift.json`; two entries remain on this branch.
- Updated user and agent changelogs.
- Added the owner-approved minimal ADR `docs/adr/0021-public-reasoning-contract.md` and its index entry.

## Scope decisions

- The original stale expected count of three known-drift entries was superseded: the fresh base contained three, therefore removing Reasoning leaves two.
- The owner explicitly allowed one minimal ADR so the architectural-change guard and CI could pass.

## Residual risks

- Reviewer noted low parser fragility from source-level Python extraction.
- The parity test intentionally covers request fields and routing enums, not every Reasoning interface.
