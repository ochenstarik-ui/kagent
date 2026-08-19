**Исполнитель: Antigravity**

# P7 — доказать продуктовую вертикаль end-to-end и доставить её PR

Правила работы — `AGENTS.md` в корне репозитория.
Репозиторий: `https://github.com/ochenstarik-ui/kagent`.
Ветка: новая `wt/p7-e2e-delivery` от свежего `origin/main`.

## Предусловие

P6 принята и влита. Использовать следующий свободный ADR после фактического main; номера
старой ветки P не считать свободными заранее.

## Работа

1. Добавить end-to-end тест без сети: task contract → model plan → runtime file edit →
   tests → commit в локальный bare remote → идемпотентный PR adapter result.
2. Добавить негативный сценарий: forbidden path или failed tests не создают commit/push/PR.
3. Устранить pytest basename collision через `--import-mode=importlib` и package layout,
   не переименовывая и не изменяя существующие тесты.
4. CI запускает `tests/unit`, reasoning и pipeline целиком; selected-file списков нет.
5. Проверить отсутствие `.worktrees`, секретных кассет, кэшей, `.pyc`, временных БД и
   чужих gitlinks в tracked tree.
6. Согласовать ADR index/changelog/capability evidence, открыть PR и приложить ссылки на
   все обязательные зелёные jobs.

## Критерий приёмки

```bash
python -m pytest tests/unit services/reasoning-engine/tests/unit services/pipeline/tests/unit -q --import-mode=importlib
ruff check services scripts tests --no-cache
python scripts/validate_repository.py
python scripts/drift_check.py
git ls-tree -r --name-only HEAD
```

- end-to-end тест доказывает изменение клонированного workspace и один commit;
- негативный сценарий доказывает отсутствие внешних Git-эффектов;
- tracked tree не содержит `.worktrees/` и случайных файлов;
- ветка опубликована, PR открыт, все обязательные jobs зелёные;
- коммит содержит `Task: p7-e2e-delivery`.

