**Исполнитель: Hermes**

# E3 — интегрировать Agent Runtime package и закрытый сервисный периметр

Правила работы — `AGENTS.md` в корне репозитория.
Репозиторий: `https://github.com/ochenstarik-ui/kagent`.
Ветка: новая `wt/e3-runtime-perimeter-integration` от свежего `origin/main`.

## Предусловие

Начинать только после принятия и слияния PR #11. PR #12 самостоятельно не сливать: его
изменения перенести или перебазировать на новый путь `services/agent_runtime`.

## Цель и работа

1. Перенести изменения PR #12 на свежий `origin/main`, не возвращая `services/agent-runtime`.
2. Обновить middleware, Docker/compose, CI и тесты на пакет `services.agent_runtime`.
3. Выбрать следующий свободный ADR после фактического main; не использовать занятый 0024.
4. Разрешить конфликты CI, changelog, compose и ADR index по смыслу, сохранив D1.
5. Доказать: внутренние порты не опубликованы; runtime и pipeline требуют служебный секрет;
   health endpoints доступны без него; gateway проксирует observability и добавляет секрет.
6. Закрыть старый PR #12 только после появления заменяющего PR и взаимной ссылки.

## Границы

Не менять sandbox policy, не добавлять mTLS и зависимости, не ослаблять проверку секрета.
Существующие тесты не менять. Не сливать PR самостоятельно.

## Критерий приёмки

```bash
python -m pytest tests/unit/test_runtime.py tests/unit/test_service_auth.py -q
python scripts/validate_repository.py
python scripts/drift_check.py
docker compose config
```

- tracked-поиск не находит живых ссылок на `services/agent-runtime`;
- compose не публикует внутренние сервисы;
- все обязательные jobs PR зелёные, приложена ссылка на run;
- коммит содержит `Task: e3-runtime-perimeter-integration`.

