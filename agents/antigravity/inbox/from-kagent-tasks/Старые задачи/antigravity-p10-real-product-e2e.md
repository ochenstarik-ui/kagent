**Исполнитель: Antigravity**

# P10 — доказать продуктовую вертикаль через production classes

Правила — `AGENTS.md`. Ветка `wt/p10-real-product-e2e` от свежего `origin/main`.

## Режим исполнения

Antigravity может делегировать позитивный E2E, негативные сценарии и CI-аудит разным
субагентам. Финальный E2E обязан запускаться после объединения их изменений через реальные
production classes на ветке оркестратора.

## Предусловие

P9 влита и полный Python CI зелёный.

## Работа

1. E2E импортирует и запускает production PipelineEngine, Reasoning Engine adapter,
   Agent Runtime tools и canonical GitManager.
2. Путь: task contract → plan → file edit → test → commit → push → PR adapter.
3. Запрещённый путь и failed test не создают Git/PR-эффектов.
4. Повтор run id не создаёт второй commit или PR.
5. Удалить старые тесты P7, которые вручную вызывают git и симулируют продуктовый pipeline;
   это новые непринятые тесты, отсутствующие в main.
6. Полный Python suite и CI проходят, tracked tree не содержит `.worktrees` и артефактов.

## Критерий приёмки

```bash
python -m pytest tests/unit services/reasoning-engine/tests/unit services/pipeline/tests/unit -q --import-mode=importlib
ruff check services scripts tests --no-cache
python scripts/validate_repository.py
python scripts/drift_check.py
```

Все jobs PR зелёные. Коммит содержит `Task: p10-real-product-e2e`.
