# ADR-0016: Computed stage status and specification drift detection

- Status: proposed
- Date: 2026-08-03

## Context

KAgent is built largely by agents, and those same agents write the reports on their own work: the roadmap, the changelog and the agent changelog. When the report is authored by the party being reported on, and nothing verifies it, the report drifts from reality — not through dishonesty, but because a plausible summary is cheaper to produce than a working feature.

The current repository already demonstrates the failure mode. Stages up to 0.8 are marked complete while continuous integration has been failing on every push to the default branch since 0.6; several components exist as files that no other module imports.

For a platform whose product claim is autonomous delivery, a self-reported status is the highest-leverage defect in the system: it disables the feedback loop that every other control depends on.

## Decision

Delivery status is computed, not written.

**Machine-readable capability inventory.** Each stage and each MVP capability is declared in a tracked file with the evidence that proves it: the evaluation cases that must pass, the end-to-end scenario that must run, the required checks, and the artifacts to produce.

**Computed status.** The roadmap status of a stage is generated from the latest continuous integration run: a capability is complete only when its declared evidence exists and passes. Manual edits of generated status blocks are rejected by a check.

**Tracked deterministic evidence (scheme B).** `docs/ci-results.json` is a versioned generator input, so deterministic and check-only roadmap generation visibly preserves the last accepted verification state. Evidence is eligible only for a successful `push` run on `refs/heads/main`, with complete and matching run ID, commit, timestamp, and URL provenance. Pull request, branch, missing, failed, skipped, cancelled, malformed, or mismatched evidence fails closed and cannot verify a capability. Only evidence named by the capability registry contributes to status; the registry's evidence composition is unchanged.

**PR-only evidence publication.** After every named evidence job succeeds on a main push, CI creates a unique automation branch containing only the tracked evidence and generated roadmap, pushes that branch normally, and opens a pull request to `main`. It never pushes directly to `main`, force-pushes, or auto-merges. Because pull requests opened by `GITHUB_TOKEN` do not normally start CI, automation explicitly dispatches CI for the created branch. Pull request, branch, and manually dispatched runs cannot publish evidence pull requests.

**Drift detection in continuous integration.** A job compares declared capabilities against observed evidence and fails the build on: a capability claimed without passing evidence, a module present in the tree but not reachable from any entry point, a documented endpoint absent from the served route table, and a documented environment variable never read.

**Reachability rule.** Code that no entry point can reach is either wired up or removed. Unreferenced modules may not be counted as delivered capability.

**Changelog obligation.** A user-visible change without a changelog entry fails the build, and an architectural change without an ADR fails the build. The existing repository rules become enforced rather than advisory.

**Honest red.** A failing build on the default branch is an incident with an owner. Continuing to add features on a red trunk is prohibited.

## Consequences

- Status becomes trustworthy enough to plan against, at the cost of admitting a lower completion level than the current documents claim.
- Repository readers can see the last accepted verified, partial, and unverified states without downloading a workflow artifact.
- Verification-state updates add a reviewable automation pull request and require live GitHub Actions validation of token permissions and explicit workflow dispatch.
- Some presently claimed stages will revert to incomplete on first application; this is a correction, not a regression.
- The reachability rule forces a decision on partially integrated work instead of letting it accumulate.
- Documentation and code are kept in sync by the build rather than by discipline.

## Related

- ADR-0005 (test oracle integrity) prevents the same substitution at task level.
- ADR-0008 (evaluation suite) supplies the evidence.
- Specification section 41.
