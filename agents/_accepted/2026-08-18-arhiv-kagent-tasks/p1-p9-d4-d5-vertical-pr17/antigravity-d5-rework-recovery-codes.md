**Исполнитель: Antigravity**

# D5 — реализовать recovery codes поверх принятой D4

Правила — `AGENTS.md`. Ветка `wt/d5-rework-recovery-codes` от свежего `origin/main`.

## Режим исполнения

Antigravity может делегировать криптографический review, API и PostgreSQL concurrency tests
непересекающимся субагентам. Интеграция с D4, security-инварианты и финальный CI остаются у
оркестратора.

## Предусловие

D4 влита. Старую D3 не продолжать: переносить только проверенную recovery-логику.

## Работа

1. Следующая миграция хранит только hash одноразовых кодов.
2. Генерировать 10 кодов с минимум 128 бит энтропии; plaintext выдаётся один раз.
3. Regeneration требует password+TOTP и атомарно отзывает старый набор.
4. Recovery login использует persistent challenge и общий лимит попыток D4.
5. Concurrent double-use даёт ровно один успех; disable TOTP отзывает набор.
6. Существующие тесты не менять; PostgreSQL recovery tests обязательны в CI и не skipped.

## Критерий приёмки

```bash
pnpm --filter @kagent/control-plane typecheck
pnpm --filter @kagent/control-plane test
pnpm typecheck && pnpm test && pnpm build
python scripts/drift_check.py
```

Все jobs PR зелёные. Коммит содержит `Task: d5-rework-recovery-codes`.
