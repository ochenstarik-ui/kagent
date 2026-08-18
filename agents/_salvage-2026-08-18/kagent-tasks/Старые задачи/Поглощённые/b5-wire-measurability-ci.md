# B5 — wire measurability into CI

Правила работы — `AGENTS.md` в корне репозитория.
Репозиторий: `https://github.com/ochenstarik-ui/kagent`, база — свежий main после принятого B4.
Ветка: `wt/b5-measurability-ci`.

## Предусловие

Начинать только после того, как B4 accepted/merged. До B4 drift-check неточен; ослаблять его запрещено.

## CI wiring

В `.github/workflows/ci.yml`:
- шаг `python scripts/drift_check.py` в существующий job python;
- отдельный job measurability: выполняет `roadmap_status.py`, публикует `ROADMAP.md`, падает при отличии от committed `ROADMAP.md`;
- `eval_suite.py` в provider-free integrity mode; draft cases только валидируются, не считаются passed.

## Known drift

После B4 drift_check должен находить:
- `services/nats/src/events.py`
- `services/auth/src/totp.py`
- `services/control-plane/src/db.ts` (если C1 ещё не принят)
- `packages/contracts/src/reasoning.ts`

Не исправлять их и не ослаблять проверку. Добавить `docs/known-drift.json`: path, reason, date/expiry и follow-up task для каждой записи. Missing task/expired entry блокирует CI. Список только сокращается; добавление требует отдельного обоснования.

## Три негативные демонстрации

1. Вручную изменить status в ROADMAP.md → guard red → откатить.
2. Добавить временный unreachable module → drift check находит → удалить.
3. Сделать временное user-visible change без CHANGELOG → check red → откатить.

Привести вывод/ссылки на три демонстрации. Временные изменения не коммитить в итог.

## Критерии

- drift_check и roadmap_status вызываются CI;
- manual roadmap edit роняет guard;
- все три negative demonstrations доказаны;
- CI green с минимальным non-expired known-drift;
- ссылки на прогоны в отчёте.

## Границы

`.github/workflows/ci.yml`, `scripts/*`, `docs/capabilities.json`, `docs/known-drift.json`, `ROADMAP.md`. Сервисы не трогать. Не наполнять eval snapshots, не исправлять найденные модули. Independent review получает полный текст. Не merge без orchestrator/user direction.
