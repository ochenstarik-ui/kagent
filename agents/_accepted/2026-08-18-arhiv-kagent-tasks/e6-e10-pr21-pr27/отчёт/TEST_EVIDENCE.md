# KAgent E6–E10 Test Evidence

**Дата:** 2026-08-12  
**Repository:** https://github.com/ochenstarik-ui/kagent

Этот документ разделяет локальные проверки, independent review и exact-commit GitHub Actions. `PASS` относится только к указанной команде/snapshot; E8 runtime failure не скрыт зелёными static/unit проверками.

## Remote CI evidence

| Task | PR head SHA | Actions run | Результат |
|---|---|---|---|
| E6 | `d9cc0bca102e11caad47f91e2c7b9453e489d5ec` | https://github.com/ochenstarik-ui/kagent/actions/runs/31526297214 | 7/7 required jobs PASS |
| E10 | `65f7c9e1e5296ff827806fdfb4593d71a49f5f70` | https://github.com/ochenstarik-ui/kagent/actions/runs/31527435722 | 7/7 required jobs PASS |
| E7 | `eaa0c84f61311b7136dc03da61341582370e5b0a` | https://github.com/ochenstarik-ui/kagent/actions/runs/31533308789 | 7 required jobs PASS; PR-only publish job SKIPPED |
| E8 | `096d7c544db342bbbdafca0cbc796e6612a57eb4` | https://github.com/ochenstarik-ui/kagent/actions/runs/31538210543 | deployment FAIL; all other required jobs PASS |
| E9 | `8e0e607966a6461ce95e207d4108d166d9c0f77a` | https://github.com/ochenstarik-ui/kagent/actions/runs/31541552195 | 7 required jobs PASS; PR-only publish job SKIPPED |

## E6 evidence

### Local acceptance

```text
python -m pytest \
  tests/unit \
  services/reasoning-engine/tests/unit \
  services/pipeline/tests/unit -q

126 passed
```

```text
ruff check services scripts tests
PASS

python scripts/drift_check.py
PASS

python scripts/validate_repository.py
PASS

git diff --check
PASS
```

### Directory-discovery negative proof

В `tests/unit` временно создавался probe test. Directory-based `pytest --collect-only` обнаружил его без изменения workflow file list; probe затем удалён. Regression test запрещает возврат named-file allowlist, `--deselect`, hidden `-k` и Ruff selection overrides.

### Independent review

```text
NO BLOCKING FINDINGS
```

### Remote jobs

- node — PASS;
- rust — PASS;
- python — PASS;
- eval — PASS;
- nats-events — PASS;
- integration — PASS;
- measurability — PASS.

## E10 evidence

### Focused and combined suites

```text
python -m pytest tests/unit/test_drift_check.py -q
23 passed
```

```text
stacked full unit suite
114 passed
```

```text
ruff check services scripts tests
PASS

python scripts/drift_check.py
PASS

python scripts/validate_repository.py
PASS

explicit unreachable modules
[]
```

### Negative demonstrations

Placeholder allowlist entry:

```text
known drift entry 0 has invalid follow_up_task
```

Temporary real orphan module:

```text
unreachable module is not allowlisted: services/e10_drift_probe_orphan.py
```

Probe был удалён после demonstration.

Boundary checks:

- lifetime 90 days — accepted;
- lifetime 91 days — rejected;
- `conftest.py` — runner entrypoint;
- configured Playwright spec — runner entrypoint.

### Independent review

```text
NO BLOCKING FINDINGS
Final verdict: APPROVE
```

### Remote CI

Run https://github.com/ochenstarik-ui/kagent/actions/runs/31527435722: node, rust, python, eval, nats-events, integration и measurability — PASS.

## E7 evidence

### Focused tests

```text
focused evidence/status suite
31 passed in 0.11s
```

Full local unit suite, Ruff, repository validation, ROADMAP deterministic guard, post-commit drift и diff check завершились PASS.

### Manual-edit negative proof

```text
ROADMAP CHECK PASSED
manual_edit_check_exit=1
```

После восстановления generated file повторный guard снова дал `ROADMAP CHECK PASSED`.

### Provenance negative coverage

Tests подтверждают, что следующие inputs не могут дать `verified`:

- PR/branch run;
- missing evidence;
- malformed evidence;
- failed/skipped/cancelled result;
- mismatched commit SHA;
- ручная правка generated ROADMAP.

### Main evidence input

Tracked source evidence использует настоящий main run `31519844840` и хранит run URL, commit SHA и timestamp. Результат generation: 19 `verified`, 4 `partial`; Stage 0.9 честно остаётся `partial`.

### Independent review

```text
Final verdict: APPROVE_WITH_NOTES
No code-level blocker
```

Operational note: permission/dispatch behavior publication automation окончательно подтверждается только настоящим main run после merge.

### Remote CI

Run https://github.com/ochenstarik-ui/kagent/actions/runs/31533308789:

- node — PASS;
- rust — PASS;
- python — PASS;
- eval — PASS;
- nats-events — PASS;
- integration — PASS;
- measurability — PASS;
- publish-verification-status — SKIPPED, ожидаемо для PR event.

## E8 evidence

### Local implementation checks

```text
python -m pytest tests/unit/test_deployment_smoke.py -q
9 passed
```

```text
python -m pytest tests/unit -q
119 passed
```

```text
ruff check scripts/deployment_smoke.py tests/unit/test_deployment_smoke.py
PASS

python -m py_compile scripts/deployment_smoke.py tests/unit/test_deployment_smoke.py
PASS

python scripts/validate_repository.py
PASS

python scripts/roadmap_status.py --check --no-run-commands
PASS

python scripts/drift_check.py   # post-commit clean tree
PASS

git diff --check
PASS
```

### Independent review

Initial staged-state drift finding был классифицирован как status-sensitive self-guard. После task commit с trailer и clean-tree drift PASS выполнен repair review:

```text
P0-P2: none
Final verdict: APPROVE
```

### Real Compose CI evidence — FAILURE

Run: https://github.com/ochenstarik-ui/kagent/actions/runs/31538210543  
Failed job: https://github.com/ochenstarik-ui/kagent/actions/runs/31538210543/job/93934323865

First causal error:

```text
ERR_PNPM_WORKSPACE_PKG_NOT_FOUND
"@kagent/contracts@workspace:*" is in the dependencies
but no package named "@kagent/contracts" is present in the workspace

target control-plane: failed at RUN corepack enable && pnpm install --prod
```

Diagnostics artifact был опубликован благодаря `if: always()`:

```text
compose-ps.txt: только заголовок NAME/IMAGE/COMMAND/SERVICE/CREATED/STATUS/PORTS
compose.log: empty
```

Это подтверждает build-time failure до создания контейнеров. Поэтому Gateway workflow, live perimeter, fail-closed runtime probe и non-empty-volume behavior в этом run не достигнуты.

Separate defect: https://github.com/ochenstarik-ui/kagent/issues/25

### Remote job matrix

- node — PASS;
- rust — PASS;
- python — PASS;
- eval — PASS;
- nats-events — PASS;
- integration — PASS;
- measurability — PASS;
- deployment — **FAIL**;
- publish-verification-status — SKIPPED.

E8 acceptance status: **implemented and reviewed; factual runtime acceptance blocked**.

## E9 evidence

### TDD evidence

Initial case contract work began from failing collection because the implementation runner did not yet exist.

Cassette hash regression guard RED:

```text
1 failed
placeholder prompt_hash != SHA-256(recorded request task)
```

После исправления:

```text
1 passed
```

Windows path-confinement RED:

```text
C:\escape.txt      DID NOT RAISE
folder\escape.txt  DID NOT RAISE
name:stream        DID NOT RAISE
3 failed
```

После исправления:

```text
8 passed in focused replay-contract file
```

Repair reviewer дополнительно доказал rejection malicious archive member с backslash и сохранение valid POSIX-relative paths.

### Per-case negative/mutation demonstration

Прямое измерение трёх состояний каждого case:

```text
bugfix_leaky_limiter: empty=False replay=True mutation=False
feature_add_endpoint: empty=False replay=True mutation=False
security_fix_header: empty=False replay=True mutation=False
```

Interpretation:

- `empty=False`: untouched snapshot rejected;
- `replay=True`: recorded response accepted;
- `mutation=False`: adjacent-breaking mutation rejected.

### Final replay metrics

```text
cases passed: 3/3
provider_calls_total: 0
tokens_spent_total: 0
average_repair_cycles: 0.6666666666666666
average_cost_usd: 0.005366666666666666
gate_passed: false
```

Per case:

| Case | Repairs | Recorded cost | Empty rejected | Replay passed | Mutation rejected |
|---|---:|---:|---|---|---|
| `bugfix_leaky_limiter` | 1 | $0.0042 | true | true | true |
| `feature_add_endpoint` | 0 | $0.0068 | true | true | true |
| `security_fix_header` | 1 | $0.0051 | true | true | true |

### Final local acceptance

```text
env -u <provider variables> python scripts/eval_suite.py --replay
3/3 PASS; provider calls/tokens 0/0

python -m pytest tests/unit -q
118 passed, 2 pre-existing FastAPI deprecation warnings

ruff check services scripts tests
PASS

python scripts/validate_repository.py
PASS

JSON Schema validation for eval/reports/latest.json
PASS

python scripts/drift_check.py   # post-commit
PASS

git diff --check + clean tree
PASS
```

### Independent review

Initial review:

```text
P0: none
P1: none
P2: none
APPROVE_WITH_NOTES
```

После Windows path-confinement repair:

```text
P0-P3: none
Final verdict: APPROVE
```

### Remote CI

Run https://github.com/ochenstarik-ui/kagent/actions/runs/31541552195:

- node — PASS;
- rust — PASS;
- python — PASS;
- eval — PASS;
- nats-events — PASS;
- integration — PASS;
- measurability — PASS;
- publish-verification-status — SKIPPED, ожидаемо для PR event.

## Known limitations and evidence boundaries

1. Все PR остаются OPEN. Green PR CI не доказывает merge в `main`.
2. E8 не имеет green deployment evidence; baseline issue #25 должен быть исправлен отдельно.
3. Локально Docker CLI был недоступен; E8 real runtime evidence получено только из GitHub Actions.
4. E7 publication automation требует post-merge main-run evidence.
5. E9 replay scrubbed provider environment, но не заявляет OS-level network sandbox; tracked fixtures и commands были проверены как stdlib-only/no-network.
6. Два FastAPI `on_event` deprecation warnings являются существующими и не связаны с E8/E9 changes.
