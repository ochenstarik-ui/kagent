# B4 — drift-check quality

Правила работы — `AGENTS.md` в корне репозитория, копия в `C:\Users\Ochenstarik\kagent-tasks\AGENTS.md`.

Репозиторий: `https://github.com/ochenstarik-ui/kagent`, база — свежий `origin/main` после PR #4.
Ветка: новая от свежего main, `wt/b4-drift-check-quality`.
Файл: `scripts/drift_check.py`. Выполняется до B5.

## Зачем

B5 подключает drift_check.py к CI как блокирующую проверку. Сейчас подключать нельзя: текущий прогон даёт 21 ложную/смешанную находку, пропускает три настоящих мёртвых модуля и самоблокируется отчётом.

Настоящие находки должны быть ровно:
- `packages/contracts/src/reasoning.ts`
- `services/nats/src/events.py`
- `services/auth/src/totp.py`
- `services/control-plane/src/db.ts`

Ложные срабатывания, которых не должно быть:
- `.venv/Lib/site-packages/_virtualenv.py`, `.venv/Scripts/activate_this.py`;
- `packages/contracts/src/index.ts`, `artifact.ts`, `event.ts`, `ids.ts`, `task.ts`;
- `artifact.test.ts`, `task.test.ts`, `tests/unit/test_*.py`;
- `services/reasoning-engine/src/server.py`, `engine.py`;
- `services/control-plane/src/domain.ts`.

Первые два настоящих модуля имеют собственные тесты; тест не делает модуль достижимым продуктом.

## Работы

1. Исключить `.venv`, `node_modules`, `target`, `dist`, `.next`, `__pycache__`, `.worktrees`, `.git`.
2. Точки входа объявлять явно: Rust binaries, service main.ts/main.py, app-объекты Dockerfile, package exports из package.json, Next.js pages. Транзитивные импорты от entry point достижимы.
3. Тесты исключить из продуктового графа; модуль, импортируемый только тестом, остаётся недостижимым.
4. Разделить обнаружение и отчёт: запись eval/report не должна менять результат второго запуска.
5. Согласовать словарь evidence между capabilities registry и drift check; неизвестный вид — ошибка с перечнем допустимых видов. Устранить `[web.dashboard] unknown evidence: build` корректным объявлением evidence, не игнорированием.

## Критерии

Два последовательных `python scripts/drift_check.py`:
- находят все четыре настоящих модуля;
- не находят ни одного перечисленного false positive;
- дают одинаковый результат;
- не выводят `unknown evidence`.

Добавить unit tests:
- транзитивно достижимый файл не отмечается;
- файл, достижимый только из теста, отмечается;
- исключённые каталоги не сканируются.

Полный вывод обоих прогонов приложить к отчёту.

## Границы

`scripts/drift_check.py`, его конфигурация, `docs/capabilities.json` только в части evidence-словаря, focused tests. Найденные модули не подключать и не удалять. CI не трогать. Push branch, создать PR, дождаться зелёного CI. Независимый review получает полный этот текст и AGENTS.md. Не merge без orchestrator/user direction.
