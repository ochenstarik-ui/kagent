**Исполнитель: Antigravity**

# P5 — единый workspace для Runtime и Git с обязательным task contract

Правила работы — `AGENTS.md` в корне репозитория.
Репозиторий: `https://github.com/ochenstarik-ui/kagent`.
Ветка: новая `wt/p5-single-workspace-git-contract` от свежего `origin/main`.

## Предусловие

D1 должна быть принята и влита. Не продолжать загрязнённый локальный main и не публиковать
старую `wt/d3-git-contour` как готовую. Перенести только нужные изменения P в чистую ветку.

## Работа

1. Создать workspace один раз и передать его абсолютный путь runtime-контексту.
2. Выполнять teardown только в `finally` после commit/push/PR либо подтверждённой ошибки.
3. Применять `allowed_paths` и `forbidden_paths` до записи и перед индексированием.
   Удалить безусловный `git add .`; индексировать только проверенные разрешённые пути.
4. Применить `allowed_actions`, `approval_required`, max time/cost/files/steps.
   Превышение — terminal result без Git-эффектов.
5. Перед ветвлением обновить refs и проверить base SHA из контракта.
6. Сделать branch/commit/push/PR идемпотентными между запусками через устойчивый ledger.
7. Добавить интеграционные тесты с локальным bare remote: runtime пишет файл, GitManager
   видит его, запрещённый путь блокируется, повтор не создаёт второй коммит.

## Границы

Без сети и GitHub в тестах. Не хранить токены в workspace/ledger/logs. Существующие тесты
не менять. Не использовать force-push.

## Критерий приёмки

```bash
python -m pytest services/pipeline/tests/unit -q --import-mode=importlib
python scripts/validate_repository.py
python scripts/drift_check.py
```

- тест доказывает единый путь runtime и Git;
- teardown не происходит до последнего Git-эффекта;
- forbidden path не попадает в index/commit;
- повтор с тем же idempotency key возвращает прежние identifiers;
- все jobs PR зелёные, коммит содержит `Task: p5-single-workspace-git-contract`.

