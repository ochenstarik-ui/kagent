**Исполнитель: Antigravity**

# P9 — интегрировать настоящий модельный цикл с P8

Правила — `AGENTS.md`. Ветка `wt/p9-integrate-model-loop` от свежего `origin/main`.

## Режим исполнения

Antigravity может делегировать Reasoning Engine, cassette и pipeline repair независимым
субагентам. Общие контракты, объединение с P8 и сквозной тест проверяет сам оркестратор.

## Предусловие

P8 влита и CI main зелёный.

## Работа

1. Выбор модели PLAN работает с дефолтным registry и privacy policy.
2. PLAN/DEVELOP используют Reasoning Engine; runtime применяет изменения в workspace P8.
3. Malformed/empty/non-2xx ответы являются ошибками без silent fallback.
4. Failed TEST создаёт REPAIR и повторный TEST; лимит завершается human decision required.
5. Cassette key детерминирован между процессами; replay запрещает provider network.
6. Объединить старые P1/P2/P6 реализации в один canonical код без параллельных механизмов.
7. Тесты используют реальные production классы с fake provider/runtime adapters.

## Критерий приёмки

```bash
python -m pytest services/reasoning-engine/tests/unit services/pipeline/tests/unit -q --import-mode=importlib
python scripts/validate_repository.py
python scripts/drift_check.py
```

Все jobs PR зелёные. Коммит содержит `Task: p9-integrate-model-loop`.
