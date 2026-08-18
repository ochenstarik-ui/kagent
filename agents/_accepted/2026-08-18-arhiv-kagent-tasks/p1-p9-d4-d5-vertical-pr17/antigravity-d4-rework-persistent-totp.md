**Исполнитель: Antigravity**

# D4 — переработать persistent TOTP без регрессии oracle

Правила — `AGENTS.md`. Ветка `wt/d4-rework-persistent-totp` от свежего `origin/main`.

## Режим исполнения

Antigravity может делегировать migration review, persistence adapter и integration scenarios
разным субагентам. Согласование транзакций, сохранность существующего oracle и полный
control-plane test остаются ответственностью оркестратора.

## Предусловие

E5 влита. Старую D2 не продолжать: использовать её только как reference diff.

## Работа

1. Сохранить существующий `auth-totp.test.ts` без изменений и обеспечить его прохождение.
2. Разделить unit-testable TOTP policy и PostgreSQL persistence adapter; unit tests не должны
   пытаться подключаться к localhost PostgreSQL.
3. Добавить миграцию persistent challenges/replay marker с актуальным свободным номером.
4. PostgreSQL integration tests обязательны и не должны быть skipped в CI.
5. Доказать cross-instance replay rejection, atomic one-time challenge и lock after 5.
6. Обновить ADR/changelog без ложного заявления о выполненных skipped tests.

## Критерий приёмки

```bash
pnpm --filter @kagent/control-plane typecheck
pnpm --filter @kagent/control-plane test
pnpm typecheck && pnpm test && pnpm build
python scripts/drift_check.py
```

Integration job выполняет новые PostgreSQL tests. Коммит содержит
`Task: d4-rework-persistent-totp`.
