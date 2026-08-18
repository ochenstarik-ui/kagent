**Исполнитель: Antigravity**

# D3 — add one-time TOTP recovery codes

Правила работы — `AGENTS.md` в корне репозитория.

Репозиторий: `https://github.com/ochenstarik-ui/kagent`.
Ветка: новая `wt/d3-totp-recovery-codes` от свежего `origin/main`.

## Предусловие

Начинать только после слияния D2 и зелёного CI свежего `main`. Использовать следующий фактически свободный номер миграции и ADR, без переименования уже принятых ADR.

## Цель

Реализовать обязательные recovery codes из `docs/KAGENT_FULL_PRODUCT_SPEC.md`, раздел 15.1, как полноценный второй путь завершения уже созданного TOTP login challenge.

## Работа

1. Добавить таблицу recovery codes следующей миграцией:
   - связь с account;
   - только криптографический hash кода, без plaintext;
   - timestamps создания/использования;
   - ограничение, исключающее повторное потребление.
2. Генерировать набор из 10 независимых кодов с криптографически стойкой случайностью. Каждый код должен иметь не менее 128 бит энтропии до форматирования. Plaintext возвращается только один раз.
3. При успешной первой активации TOTP вернуть recovery codes один раз. Не включать их в status/whoami/logs/errors.
4. Добавить authenticated endpoint регенерации:
   - требует пароль и действующий TOTP;
   - атомарно инвалидирует весь прежний набор;
   - возвращает новый набор один раз;
   - generic failure не раскрывает, какой фактор неверен.
5. Добавить `POST /v1/auth/login/recovery` с `challengeId` и recovery code:
   - использует тот же persistent challenge и общий лимит попыток D2;
   - атомарно потребляет challenge и recovery code;
   - выдаёт ровно одну session/token pair;
   - повтор кода или challenge отклоняется как `Invalid credentials`.
6. При disable TOTP удалить/инвалидировать все recovery codes аккаунта в согласованной операции.
7. Добавить unit и PostgreSQL integration tests: plaintext нигде не хранится, набор показывается один раз, regeneration отзывает старый набор, concurrent double-use даёт один успех, лимит challenge общий для TOTP и recovery.
8. Обновить API contract/version при необходимости, web-клиент только в объёме отображения одноразового набора после activation/regeneration, `CHANGELOG.md`, threat model и capability evidence.
9. Если выбран алгоритм hash или новая библиотека, отдельно обосновать выбор и лицензию. Для случайного 128-bit кода допустим встроенный `node:crypto`; быстрый hash допустим только потому, что исходный код имеет высокую энтропию.

## Границы

Не добавлять WebAuthn/passkeys, email-delivery или обход второго фактора администратором. Recovery code не отключает TOTP автоматически. Существующие тесты не менять.

## Критерий приёмки

- в БД, логах и API после первичной выдачи нет plaintext recovery codes;
- один recovery code успешно завершает один действующий challenge только один раз;
- конкурентное использование одного кода даёт ровно один успех;
- regeneration немедленно отзывает старый набор;
- disable TOTP отзывает набор;
- ошибки unknown/expired/used/wrong одинаковы;
- `pnpm --filter @kagent/control-plane typecheck`;
- `pnpm --filter @kagent/control-plane test`;
- PostgreSQL integration tests зелёные;
- `pnpm typecheck && pnpm test && pnpm build`;
- `python scripts/drift_check.py`;
- все обязательные jobs PR зелёные, приложена ссылка на run.

Коммит содержит строку `Task: d3-totp-recovery-codes`. Не force-push, не сливать PR самостоятельно.
