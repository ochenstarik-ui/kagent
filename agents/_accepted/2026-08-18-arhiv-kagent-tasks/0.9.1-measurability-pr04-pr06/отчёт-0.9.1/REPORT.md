# KAgent 0.9.1 — B2 measurability sanitize

## Статус

- B2: **implemented / locally verified / independently reviewed**
- B3: **blocked** — PR #3 ещё открыт, `origin/main` не содержит 0.9.0
- Ветка: `wt/kagent-091-measurability`
- Checkpoint: `9e08aca`
- B2 commit: `1bbd447`
- Push/PR 0.9.1: не выполнялись, чтобы последующий обязательный rebase на merged `origin/main` не потребовал force-push

## Изменения B2

- удалены конфликтующие незакоммиченные ADR-0008/0016; сравнение с PR #2 не выявило уникального решения для ADR-0021;
- из `docs/capabilities.json` удалены вручную выставленные статусы этапов;
- `roadmap_status.py` вычисляет `verified / partially verified / unverified` только из фактических evidence;
- отсутствие CI result и manual claim не засчитываются как доказательство;
- общие evidence-команды кэшируются в рамках генерации;
- пять пустых eval-кейсов помечены `draft`;
- draft-кейсы исключаются из метрик и gate, а draft с runnable-полями отклоняется;
- добавлены `tests/unit/test_measurability.py` и `tests/unit/test_eval_suite.py`.

## Честные ограничения

- полный Python unit suite не собирается из-за существующих проблем окружения: отсутствует `nats`, несовместим `pydantic_core`, не разрешается `services.agent_runtime`;
- `drift_check.py` ожидаемо завершается с exit 1 и показывает текущий drift;
- текущая реализация drift обнаруживает больше четырёх ожидаемых недостижимых модулей; это необходимо нормализовать в B3, не ослабляя контроль;
- все eval-кейсы пока draft, поэтому `gate_passed=false` — это корректное поведение;
- B3 не начат: PR #3 не merged.

## Побочные файлы, не включённые в коммиты

- `.env.example`
- `pyproject.toml`
- `services/gateway/Cargo.lock`
- `uv.lock`
