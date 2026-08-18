**Исполнитель: Antigravity**

# P8 — подключить GitManager к production pipeline

Правила — `AGENTS.md`. Ветка `wt/p8-wire-git-manager` от свежего `origin/main`.

## Режим исполнения

Antigravity может оркестрировать независимые подзадачи по contract, ledger и тестовому bare
remote. Подключение к PipelineEngine, устранение дублей и финальная проверка остаются у
Antigravity на одной интеграционной ветке.

## Предусловие

E5 влита. Старые P-ветки не продолжать и не сливать. Код можно переносить выборочно,
но итог обязан иметь один canonical GitManager, contract и ledger.

## Работа

1. Production `PipelineEngine` создаёт один workspace и передаёт его runtime и GitManager.
2. Подключить `allowed_paths`, `forbidden_paths`, actions, approval и все лимиты.
3. Индексировать только проверенные пути; `git add .` запрещён.
4. Commit/push/PR происходят только после зелёных tests; teardown — после последнего эффекта.
5. Ledger устойчив между процессами и делает branch/commit/push/PR идемпотентными.
6. Удалить или объединить дубли `git.py`/ `git_manager.py`, `ledger.py`.
7. Тест должен вызывать production `PipelineEngine`, а не GitManager отдельно.

## Критерий приёмки

```bash
python -m pytest services/pipeline/tests/unit -q --import-mode=importlib
python scripts/validate_repository.py
python scripts/drift_check.py
```

`rg GitManager services/pipeline/src/pipeline.py` показывает реальное подключение.
Все jobs PR зелёные. Коммит содержит `Task: p8-wire-git-manager`.
