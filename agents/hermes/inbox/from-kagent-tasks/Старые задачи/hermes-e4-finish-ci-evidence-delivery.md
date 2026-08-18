**Исполнитель: Hermes**

# E4 — довести CI evidence до опубликованного проверяемого результата

Правила работы — `AGENTS.md` в корне репозитория.
Репозиторий: `https://github.com/ochenstarik-ui/kagent`.
Исходная работа: карточка `t_f3a307de`, ветка `wt/e2-ci-evidence`.

## Работа

1. Сохранить принадлежащий E2 diff и перенести его в чистую ветку
   `wt/e4-ci-evidence-delivery` от свежего `origin/main`.
2. Довести evidence jobs и выполненных команд до формата с run id, commit SHA, conclusion,
   временем и provenance.
3. Запускать `measurability` после зависимых jobs даже при failure; skipped/cancelled/failure
   не могут дать ложный `verified`.
4. Передать evidence в `roadmap_status.py --ci-results`; сохранить строгие
   `verified`, `partial`, `unverified`.
5. Покрыть тестами неполный evidence, неизвестный job, несовпадающий SHA и failed job.
6. Получить реальный CI run и приложить фрагмент ROADMAP со статусами и ссылкой.

## Границы

Не менять `docs/capabilities.json` ради статусов, не подделывать command evidence, не
обращаться к GitHub API с токеном. Существующие тесты не менять.

## Критерий приёмки

```bash
python -m pytest tests/unit/test_ci_evidence.py -q
python scripts/roadmap_status.py --check --no-run-commands
python scripts/validate_repository.py
python scripts/drift_check.py
```

- рабочее дерево чистое, ветка опубликована, открыт PR;
- evidence содержит реальные conclusions обязательных jobs;
- коммит содержит `Task: e4-ci-evidence-delivery`.

