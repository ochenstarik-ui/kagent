# TEST_EVIDENCE — KAgent 0.9.1 B2

## Focused tests

```text
uv run --no-project --with pytest pytest \
  tests/unit/test_measurability.py tests/unit/test_eval_suite.py -q

......... [100%]
9 passed
```

## Ruff

```text
uvx ruff check scripts/roadmap_status.py scripts/eval_suite.py \
  tests/unit/test_measurability.py tests/unit/test_eval_suite.py

All checks passed!
```

## Roadmap status

```text
python scripts/roadmap_status.py --dry-run
exit 0
stages 0.1–0.9: [unverified]
```

Полный вывод: `ROADMAP_STATUS.txt`.

## Drift check

```text
python scripts/drift_check.py
exit 1 — DRIFT CHECK FAILED
```

Это ожидаемый B2 результат: проверка выполняется и раскрывает фактические расхождения. Полный вывод: `DRIFT_CHECK.txt`.

## Eval replay

```json
{
  "autonomy_rate": 0.0,
  "results": [],
  "gate_passed": false
}
```

Команда завершилась exit 0. Все пять placeholder-кейсов исключены как draft. Полный вывод: `EVAL_REPLAY.txt`.

## Full unit suite

Не пройден: collection блокируется существующими зависимостями/импортами (`nats`, `pydantic_core`, `services.agent_runtime`). Не выдаётся за PASS.
