# B3 — wire KAgent measurability into CI

Rules: read `C:\Users\Ochenstarik\kagent-tasks\AGENTS.md`.
Repository: `C:\Users\Ochenstarik\kagent`
Base: current `origin/main` after merged PR #3 and PR #4.
Branch: `wt/kagent-091-wire-ci` (successor branch; original B2 branch was merged by PR #4 and must not be force-pushed).

## Preconditions

Verify PR #3 and PR #4 are merged and fetch `origin/main`. Work only from the current merged main. Do not rebase or rewrite the already merged B2 branch.

## Problem

`scripts/roadmap_status.py`, `scripts/drift_check.py`, and `scripts/eval_suite.py` now exist but are not wired into CI. The computed status is still declarative until CI invokes and verifies these scripts.

## 1. Wire CI

Modify `.github/workflows/ci.yml`:

- In existing Python job run `python scripts/drift_check.py`.
- Add a separate `measurability` job that runs `roadmap_status.py`, publishes generated `docs/ROADMAP.md` as a CI artifact, and fails if generated content differs from committed `docs/ROADMAP.md`.
- Run `eval_suite.py` in provider-free integrity/replay mode. All existing eval cases are drafts, so the job validates contracts/integrity but must not claim cases passed.

## 2. Known drift with expiry

The first drift run must find at least these four unreachable modules:

- `services/nats/src/events.py`
- `services/auth/src/totp.py`
- `services/control-plane/src/db.ts`
- `packages/contracts/src/reasoning.ts`

Do not connect/delete those modules and do not weaken the check. Add `docs/known-drift.json`; each allowlisted entry must contain path, reason, expiry date, and follow-up task ID. Missing task/expiry or expired entry fails CI. Unknown drift beyond the allowlist fails CI. Keep the list minimal and shrinking.

Normalize reachability so dependencies, tests, `.venv`, generated files, and ordinary reachable modules are not false positives. The four required modules must still be detected before allowlist filtering. Add focused tests for the known-drift schema, expiry, and exact four-module detection.

Ensure every evidence reference in `docs/capabilities.json` resolves to a concrete command, CI job, eval case, or artifact. Generic/nonexistent job name `ci` must not create false verification.

## 3. Manual edit negative check

Prove the generated-roadmap guard:
1. generate committed `docs/ROADMAP.md` deterministically;
2. make a temporary manual status edit;
3. run the same guard and capture its nonzero result;
4. restore the file;
5. run the guard successfully.
Do not commit the temporary edit.

## Scope

Allowed: `.github/workflows/ci.yml`, `scripts/*`, `docs/capabilities.json`, `docs/known-drift.json`, `docs/ROADMAP.md`, and focused tests for these scripts.
Do not edit services, gateway, control-plane, eval case payloads, product code, or unrelated files.

## Acceptance

- Branch starts from merged main containing 0.9.0 and B2.
- CI invokes drift check, computed roadmap guard/artifact upload, and draft-only eval integrity.
- Drift detection proves all four required unreachable modules and green CI uses only valid non-expired known-drift entries.
- Temporary manual status edit makes the roadmap guard fail; restored generated file passes.
- Focused tests, Ruff, JSON/YAML parse, and relevant Python checks pass.
- Push branch and create PR.
- Wait for GitHub Actions; all jobs green.
- Independent review receives this full task and AGENTS.md. Do not merge without orchestrator/user direction.

## Reporting

Record exact commands/output, CI URL, changed files, known drift, manual-edit negative check, and anything not run. Save no secrets.
