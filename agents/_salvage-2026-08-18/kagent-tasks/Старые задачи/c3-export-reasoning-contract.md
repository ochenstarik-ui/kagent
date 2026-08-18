# C3 — export reasoning contract

Правила работы — `AGENTS.md` в корне репозитория.

Репозиторий: `https://github.com/ochenstarik-ui/kagent`, база — свежий `main`
Ветка: `wt/c3-reasoning-contract`
Файлы: `packages/contracts/src/index.ts`, новый тест, `docs/known-drift.json`.
Зависимостей нет; не пересекается с c1, c4, c5.

## Problem

`packages/contracts/src/reasoning.ts` не экспортируется. Python reasoning-engine дублирует понятия; ADR-0002 запрещает два независимых контракта.

## Work

1. Добавить `export * from "./reasoning.js";` в `packages/contracts/src/index.ts`.
2. Добавить CHANGELOG.md и AGENT_CHANGELOG.md: аддитивная публичная поверхность @kagent/contracts.
3. Добавить contract parity test между TypeScript `DecideRequest`, `Capability`, `PrivacyClass`, `ExecutionMode`, `TaskCategory` и простыми enum/fields из Python server.py/engine.py. Не использовать хрупкий regex по всему файлу; разбирать целевые секции. При реальном drift не подгонять молча: сверить с ТЗ и объяснить выбор.
4. Удалить reasoning.ts из docs/known-drift.json; список только сокращается.

## Acceptance

- `pnpm --filter @kagent/contracts typecheck`
- `pnpm --filter @kagent/contracts test`
- `pnpm typecheck`
- `pnpm build`
- `python scripts/drift_check.py`
- reasoning.ts не в drift output; known-drift осталось 2 записи.
- вручную добавить лишнее enum-значение в одной стороне, показать RED, откатить, приложить вывод.
- зелёный CI URL.

## Boundaries

`packages/contracts`, новый тест, `docs/known-drift.json`, `CHANGELOG.md`, `AGENT_CHANGELOG.md`. Python service не переписывать кроме доказанного конфликта с spec. TDD, no existing-test weakening, no force push, do not merge.
