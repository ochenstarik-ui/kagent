# B2 — sanitize measurability work

Rules: read `C:\Users\Ochenstarik\kagent-tasks\AGENTS.md`.
Worktree: `C:\Users\Ochenstarik\kagent\.worktrees\t_e15a6516`
Branch: `wt/kagent-091-measurability`

## Starting point
0.9.1 was half implemented and uncommitted. The worktree contained three scripts, docs/capabilities.json, five eval cases with placeholder archives, tests/unit, duplicate ADRs, and unrelated `.env.example`, `pyproject.toml`, `uv.lock`, `services/gateway/Cargo.lock`. Checkpoint commit `9e08aca` preserved scripts, registry, eval, and tests. Sanitize commit is `1bbd447`.

## Requirements

1. Preserve work in a checkpoint before sanitizing. Unrelated `.env.example`, `services/gateway/Cargo.lock`, `uv.lock`, and `pyproject.toml` must not be committed.

2. Duplicate ADR numbers: newly created `docs/adr/0008-measurability-and-computed-status.md` and `docs/adr/0016-spec-drift-and-eval-integrity.md` conflict with accepted decisions in PR #2: `0008-platform-evaluation-suite.md` and `0016-computed-stage-status.md`. Delete the duplicate files. Create ADR-0021 only if genuinely unique decisions are absent from upstream ADR-0008/0016, and then status must be `proposed`, never executor-declared `accepted`.

3. Remove manually declared stage statuses from `docs/capabilities.json`. Registry declares what must be proven, not current completion. Status must be computed by `roadmap_status.py`; absent evidence means `unverified`. Every evidence item must be verifiable: CI job name, eval case, or concrete artifact. A list of existing source files alone is not proof.

4. Run `python scripts/roadmap_status.py`/`--dry-run`; output must show statuses derived from evidence, with most expected `unverified`, not copied declarations.

5. The five eval `base.tar.gz` files are 64-byte empty placeholders. Either make one real case and remove others, or mark all placeholder contracts `draft` and exclude drafts from metrics. Draft cases must not count as active/passing and must not make an empty suite look ready. `eval_suite.py` must not count `draft`.

6. Run `python scripts/drift_check.py` and record exact discrepancies. A nonzero exit exposing current drift is acceptable/expected for B2; do not weaken it.

## Acceptance
- Work committed with no loss.
- No duplicate ADR numbers; no executor-created accepted ADR.
- `roadmap_status.py` exits successfully and prints evidence-derived statuses.
- `drift_check.py` executes and prints discrepancies.
- No eval case appears runnable when it is only a placeholder.
- Exact outputs attached to report/Kanban.

## Boundaries
Only the listed measurability/eval files. Do not rebase. Do not touch CI (B3), gateway, or control-plane. Do not commit `.env.example`, `services/gateway/Cargo.lock`, `uv.lock`, or unrelated `pyproject.toml`.
