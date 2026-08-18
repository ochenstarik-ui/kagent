**Исполнитель: Antigravity**

# D2 — persist TOTP challenges and replay protection

Правила работы — `AGENTS.md` в корне репозитория.

Репозиторий: `https://github.com/ochenstarik-ui/kagent`.
Ветка: новая `wt/d2-persist-totp-state` от свежего `origin/main`.

## Предусловие

Начинать только после слияния PR #10 и D1, при зелёном CI свежего `main`. Проверить, что TOTP ADR имеет номер 0023 и что следующий номер миграции свободен; не угадывать номер при конфликте.

## Проблема

C4 хранит login challenges и последний принятый TOTP time-step в process-local `Map`. При нескольких экземплярах Control Plane это требует sticky routing и допускает повторное использование кода на другом экземпляре. Перезапуск процесса также сбрасывает replay state.

## Работа

1. Добавить следующую последовательную SQL-миграцию:
   - persistent login challenges: непрозрачный идентификатор или его hash, account id, expiry, attempt count, consumed/locked state и timestamps;
   - persistent last accepted TOTP step для аккаунта.
2. Перевести `AuthStore` с обеих in-memory maps на PostgreSQL.
3. Все security-sensitive переходы выполнять атомарно:
   - challenge можно успешно потребить только один раз;
   - попытки увеличиваются без lost update;
   - пятая неверная попытка блокирует challenge;
   - expired/locked/unknown/consumed challenge дают одинаковый `Invalid credentials`;
   - TOTP step принимается только если он строго больше сохранённого, включая конкурентные запросы с разных экземпляров.
4. Новый secret и disable сбрасывают replay marker в той же согласованной операции. Disable удаляет/инвалидирует активные challenges аккаунта.
5. Добавить PostgreSQL integration tests с двумя экземплярами `AuthStore`, доказывающие cross-instance success, replay rejection и конкурентное one-time consumption.
6. Удалить устаревший cleanup/map код. Обновить ADR 0023: process-local limitation больше не действует.
7. Обновить changelog, threat model только если меняется поверхность угроз, capability evidence и generated roadmap по правилам репозитория.

## Границы

Не добавлять recovery codes, WebAuthn, Redis или новый auth-service. Не менять формат JWT и не ослаблять generic auth errors. Существующие тесты не менять.

## Критерий приёмки

- миграции применяются к пустой БД и поверх текущей схемы;
- integration test доказывает работу между двумя `AuthStore`;
- два конкурентных запроса с одним challenge/code создают ровно одну session;
- повтор принятого TOTP step на другом экземпляре отклоняется;
- после 5 ошибок challenge не восстанавливается правильным кодом;
- `pnpm --filter @kagent/control-plane typecheck`;
- `pnpm --filter @kagent/control-plane test`;
- `pnpm typecheck && pnpm test && pnpm build`;
- `python scripts/drift_check.py`;
- все обязательные jobs PR зелёные, приложена ссылка на run.

Коммит содержит строку `Task: d2-persist-totp-state`. Не force-push, не сливать PR самостоятельно.
