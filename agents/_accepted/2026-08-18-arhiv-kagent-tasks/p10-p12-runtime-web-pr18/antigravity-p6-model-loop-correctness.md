**Исполнитель: Antigravity**

# P6 — исправить модельный цикл и воспроизводимость Reasoning/Pipeline

Правила работы — `AGENTS.md` в корне репозитория.
Репозиторий: `https://github.com/ochenstarik-ui/kagent`.
Ветка: новая `wt/p6-model-loop-correctness` от свежего `origin/main`.

## Предусловие

P5 принята и влита. Ветка создаётся от актуального `origin/main`.

## Работа

1. Обеспечить работоспособный PLAN с дефолтным registry: privacy/capability выбирают
   допустимую модель либо возвращают явную диагностируемую ошибку.
2. Неразбираемый JSON плана/патча завершает шаг ошибкой с raw artifact; silent fallback запрещён.
3. HTTP/non-success runtime и пустой/malformed provider response никогда не дают PASSED.
   `success=True` выставляется только после проверки содержимого.
4. После failed TEST создавать REPAIR с диагностическим контекстом; строго соблюдать
   `max_repair_cycles`, затем возвращать human decision required.
5. Сделать cassette key детерминированным по каноническому запросу и модели, без временного
   request id. Replay нового процесса находит запись и не вызывает сеть.
6. Проверить fallback models, timeout/cancellation, токены и фактическую стоимость попыток.
   Секреты не попадают в ответы, artifacts и telemetry.
7. Добавить новые негативные тесты; существующие тесты не менять.

## Критерий приёмки

```bash
python -m pytest services/reasoning-engine/tests/unit services/pipeline/tests/unit -q --import-mode=importlib
ruff check services/reasoning-engine services/pipeline --no-cache
python scripts/validate_repository.py
python scripts/drift_check.py
```

- TEST-fail → REPAIR → TEST-pass доказан отдельным тестом;
- replay проходит в новом engine при запрещённом provider network;
- malformed/empty response и runtime 500 завершаются ошибкой;
- все jobs PR зелёные, коммит содержит `Task: p6-model-loop-correctness`.

