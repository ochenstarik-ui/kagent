**ЗАКРЫТА 2026-08-11 — предмет исчез.**

`tests/unit/test_totp.py` удалён вместе с переходом TOTP на TypeScript: файл импортировал
`services.auth`, которого больше нет. Удаление сделано внутри задачи P11/P12 попутно, а не
этой постановкой — то есть работа выполнена, но другим исполнителем и в чужом коммите.

Остаток задачи — перевод CI с поимённого списка на полный каталог — целиком покрывается E6,
у которой предусловие снято.

---

**Исполнитель: Hermes**

# E5 — восстановить полный Python test collection baseline

Правила работы — `AGENTS.md` в корне репозитория.
Репозиторий: `https://github.com/ochenstarik-ui/kagent`.
Ветка: новая `wt/e5-python-collection-baseline` от свежего `origin/main`.

## Режим исполнения

Hermes может быть оркестратором: делегировать аудит импортов, CI и package layout
непересекающимся субагентам. Итоговый diff, решение по legacy-тесту и полный collection
проверяет и сдаёт Hermes на одной интеграционной ветке.

## Предусловие и работа

Начинать после слияния D1. Сначала воспроизвести полный collection и перечислить ошибки.

1. Установить актуальный пакет и тестовый слой TOTP после C4.
2. Устранить устаревший импорт `services.auth` на стороне production/package layout.
   Не добавлять копию сервиса, `sys.path` hack или динамический import.
3. Если существующий тест действительно требует изменения или удаления, остановиться и
   запросить явное разрешение владельца: запрет AGENTS остаётся в силе.
4. Настроить CI на полный `tests/unit` и service unit suites без selected-file списка.
5. Устранить basename collision через import mode/package layout, не переименовывая тесты.

## Критерий приёмки

```bash
python -m pytest tests/unit services/reasoning-engine/tests/unit services/pipeline/tests/unit --collect-only -q --import-mode=importlib
python -m pytest tests/unit/test_runtime.py -q
python scripts/validate_repository.py
python scripts/drift_check.py
```

- collection без ошибок и CI выполняет ту же область;
- существующие тесты не изменены без отдельного разрешения;
- все jobs PR зелёные, коммит содержит `Task: e5-python-collection-baseline`.
