**Исполнитель: Hermes**

# D1 — normalize the Python Agent Runtime package

Правила работы — `AGENTS.md` в корне репозитория.

Репозиторий: `https://github.com/ochenstarik-ui/kagent`.
Ветка: новая `wt/d1-agent-runtime-package` от свежего `origin/main`.

## Предусловие

Не начинать, пока PR #8, #9 и #10 не влиты и CI свежего `main` не зелёный. После этого выполнить `git fetch origin` и создать ветку строго от `origin/main`.

## Проблема

Полный сбор unit-тестов сейчас падает на `tests/unit/test_runtime.py`:

```
ModuleNotFoundError: No module named 'services.agent_runtime'
```

Причина — код лежит в каталоге `services/agent-runtime`, который нельзя импортировать как Python-пакет `services.agent_runtime`. CI не видит дефект, потому что Python job запускает только вручную перечисленное подмножество тестов.

## Работа

1. Переименовать Python-каталог в импортируемый `services/agent_runtime`.
2. Обновить все реальные ссылки на старый путь:
   - Docker/build context и compose;
   - capability registry и generated roadmap inputs;
   - документацию и скрипты;
   - импорты.
3. Не оставлять копию реализации, `sys.path` hacks, динамический import по файловому пути или compatibility-каталог с дублированием кода.
4. Подключить `tests/unit/test_runtime.py` к обязательному Python CI evidence. Предпочтительно запускать весь `tests/unit`, если после слияния C4 он проходит; иначе расширить явный список и в отчёте назвать оставшийся независимый blocker.
5. Обновить `CHANGELOG.md`, `AGENT_CHANGELOG.md` и capability artifacts/evidence только там, где это требуется drift-check.

## Границы

Не рефакторить поведение Agent Runtime, не менять sandbox policy и tool permissions. Не исправлять попутно весь накопленный Ruff backlog. Существующие тесты не менять.

## Критерий приёмки

- `python -m pytest tests/unit/test_runtime.py -q`;
- `python -m pytest tests/unit --collect-only -q` без import errors;
- `python scripts/validate_repository.py`;
- `python scripts/drift_check.py`;
- поиск по tracked-файлам не находит живых ссылок на `services/agent-runtime`;
- обязательный Python CI job действительно запускает runtime-тест;
- все обязательные jobs PR зелёные, приложена ссылка на run.

Коммит содержит строку `Task: d1-agent-runtime-package`. Не force-push, не сливать PR самостоятельно.
