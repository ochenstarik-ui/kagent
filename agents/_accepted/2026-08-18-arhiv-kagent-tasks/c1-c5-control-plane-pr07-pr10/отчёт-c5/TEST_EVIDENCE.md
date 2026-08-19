# C5 Test Evidence

## Final local verification

- Focused Ruff on the C5 event package/tests with `E,BLE` and repository line/import allowances — PASS.
- Event, pipeline and orchestrator focused tests — `14 passed, 2 deprecation warnings`.
- Earlier focused C5 event/pipeline tests — `9 passed`.
- `python scripts/drift_check.py` — PASS; NATS is absent from unreachable drift.
- `python scripts/roadmap_status.py --check --no-run-commands` — PASS.
- `roadmap_status.py` with actual final `python=success` and `nats-events=success` CI conclusions — `[x] [nats.events] ... verified`.
- `git diff --check origin/main...HEAD` — PASS.
- Final worktree — clean.

## GitHub Actions

Final run: https://github.com/ochenstarik-ui/kagent/actions/runs/31364595568

- node — SUCCESS
- rust — SUCCESS
- python — SUCCESS
- measurability — SUCCESS
- nats-events — SUCCESS
- integration — SUCCESS

The `nats-events` job starts `nats:2.11-alpine` with JetStream and proves publish, durable receive and stream reuse against the real broker.
