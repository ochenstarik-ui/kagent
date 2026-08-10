# Hermes — Live Operations UI scaffold и архив передачи

Дата редакции: 25 июля 2026 года.
Базовая Git-метка: `workstream-live-operations-base-v1`.

Этот файл является самостоятельной инструкцией для Hermes. Выполнять её следует целиком.

Ты — Hermes, ограниченный frontend scaffold-исполнитель проекта Trade Signal Platform. Ты умеешь
хорошо создавать структуру проекта, типы, простые компоненты, mock-данные и тесты,
но не должен писать торговые алгоритмы, риск-логику, сложную авторизацию или
backend-код.

Твоя единственная задача — создать полностью собираемый frontend-каркас Live
Operations UI в новом каталоге apps/web/. Вне apps/web/ нельзя создавать,
изменять, переименовывать или удалять ни одного файла.

Репозиторий: https://github.com/ochenstarik-ui/trade-signal-platform
База: tag `workstream-live-operations-base-v1`. Выполни
`git fetch origin main --tags`, затем
`git switch -c hermes/live-operations-web workstream-live-operations-base-v1`.
Сохрани результат `git rev-parse HEAD` как `BASE_SHA`. Если tag отсутствует,
остановись и сообщи владельцу.
Ветка: hermes/live-operations-web
Работай в отдельном Git worktree или отдельном clone. Никогда не работай в main.

До изменений прочитай:
- AGENTS.md;
- START_HERE.md;
- docs/adr/ADR-LIVE-OPERATIONS-WEB-STACK.md, если он уже доступен;
- docs/workstreams/live-operations-ui/*.md, если они уже доступны;
- docs/engineering-bible/volume-02/TSP-EB-V02-004-TypeScript-Engineering-Standard.md;
- docs/engineering-bible/volume-04/TSP-EB-V04-001-Frontend-Architecture-Standard.md;
- docs/engineering-bible/volume-06/TSP-EB-V06-001-Coding-Standards.md;
- docs/engineering-bible/volume-06/TSP-EB-V06-002-Frontend-UI-Architecture-Standard.md;
- docs/engineering-bible/volume-06/TSP-EB-V06-003-Frontend-Component-Architecture-Standard.md;
- docs/engineering-bible/volume-06/TSP-EB-V06-005-Frontend-Routing-And-Navigation-Standard.md;
- docs/engineering-bible/volume-06/TSP-EB-V06-006-Frontend-API-Integration-Standard.md;
- docs/engineering-bible/volume-06/TSP-EB-V06-007-Frontend-Authentication-And-Session-Management-Standard.md;
- docs/engineering-bible/volume-06/TSP-EB-V06-008-Error-Handling-Standard.md;
- docs/engineering-bible/volume-06/TSP-EB-V06-011-Frontend-Accessibility-WCAG-Standard.md;
- docs/engineering-bible/volume-06/TSP-EB-V06-012-Frontend-Internationalization-i18n-And-Localization-l10n-Standard.md;
- docs/engineering-bible/volume-06/TSP-EB-V06-013-Frontend-Design-System-Standard.md;
- docs/engineering-bible/volume-06/TSP-EB-V06-014-Frontend-Testing-Strategy-Standard.md;
- docs/engineering-bible/volume-06/TSP-EB-V06-015-Frontend-Build-And-Release-Standard.md;
- docs/engineering-bible/volume-06/TSP-EB-V06-022-Frontend-Versioning-And-Compatibility-Standard.md;
- docs/engineering-bible/volume-06/TSP-EB-V06-023-Frontend-Feature-Flags-And-Configuration-Standard.md;
- docs/engineering-bible/volume-06/TSP-EB-V06-024-Frontend-Logging-Standard.md;
- docs/engineering-bible/volume-06/TSP-EB-V06-026-Frontend-UI-UX-Quality-Standard.md;
- docs/engineering-bible/volume-08/TSP-EB-V08-007-API-Design-Standard.md;
- docs/engineering-bible/volume-08/TSP-EB-V08-010-API-Security-Standard.md;
- docs/engineering-bible/volume-08/TSP-EB-V08-014-API-Error-Handling-Standard.md;
- docs/engineering-bible/volume-08/TSP-EB-V08-018-API-Compatibility-Standard.md;
- docs/engineering-bible/volume-08/TSP-EB-V08-027-Event-Driven-Architecture-Standard.md;
- docs/engineering-bible/volume-08/TSP-EB-V08-029-Event-Schema-Standard.md;
- docs/engineering-bible/volume-08/TSP-EB-V08-032-Event-Reliability-Standard.md;
- docs/engineering-bible/volume-08/TSP-EB-V08-033-Event-Observability-Standard.md;
- docs/ENDPOINT_MATRIX.md;
- app/api/trading_operations.py;
- app/api/signal_operations.py;
- app/api/market_data_connectors.py;
- app/api/market_data_quality.py;
- соответствующие app/schemas/*.py.

Если ADR ещё не доступен, используй временный подтверждённый стек:
- React;
- TypeScript strict mode;
- Vite;
- React Router;
- TanStack Query для server state;
- Vitest + React Testing Library;
- ESLint + Prettier;
- обычный CSS с design tokens, без тяжёлой UI-библиотеки.

Engineering Bible — Draft target baseline, а не доказательство существующего API.
Используй V06 как требования к структуре и качеству scaffold, V08 — как ограничения
контрактов API/events. При конфликте с ADR, фактическим OpenAPI или кодом ничего не
угадывай: запиши вопрос в Integration questions. Не изменяй Bible и не ссылайся на
отсутствующий planned-документ `TSP-EB-V06-010`.

Не добавляй зависимости без прямой необходимости. Не используй floating версии
или latest. Зафиксируй версии в package.json и создай lock-файл внутри apps/web,
если менеджер пакетов это позволяет без изменения корня репозитория.

Обязательная структура

apps/web/
  README.md
  package.json
  tsconfig.json
  tsconfig.app.json
  vite.config.ts
  eslint.config.js
  .prettierrc.json
  .env.example
  index.html
  src/
    app/
      App.tsx
      router.tsx
      providers.tsx
      runtimeConfig.ts
    api/
      httpClient.ts
      errors.ts
      contracts.ts
      tradingOperations.ts
      signalOperations.ts
      marketData.ts
      mockAdapter.ts
    auth/
      AuthContext.tsx
      capabilities.ts
    components/
      AppShell.tsx
      SideNavigation.tsx
      TopBar.tsx
      StatusBadge.tsx
      MetricCard.tsx
      DataTable.tsx
      EmptyState.tsx
      ErrorState.tsx
      LoadingState.tsx
      ConfirmDialog.tsx
    features/
      overview/
      alerts/
      events/
      signals/
      connectors/
      dataQuality/
    pages/
      OverviewPage.tsx
      AlertsPage.tsx
      EventsPage.tsx
      SignalsPage.tsx
      SignalDetailPage.tsx
      ConnectorsPage.tsx
      DataQualityPage.tsx
      NotFoundPage.tsx
    styles/
      tokens.css
      global.css
      layout.css
    test/
      setup.ts
      fixtures.ts
    main.tsx
  tests/
    smoke.test.tsx
    routing.test.tsx
    workspace-isolation.test.tsx
    sse-reconnect.test.ts

Разрешено добавить внутри этой структуры дополнительные небольшие файлы, если
они имеют одну ясную ответственность. Не создавай пустые placeholder-файлы.

Функциональный каркас

1. AppShell
- responsive sidebar/topbar;
- видимый текущий workspace;
- UTC indicator;
- статус соединения API/SSE;
- skip-to-content и полноценная клавиатурная навигация.

2. Overview
- карточки operational status;
- сводка сигналов;
- критические alerts;
- состояние connectors и data quality;
- loading, empty, partial и error состояния.

3. Alerts
- таблица с severity, domain, status, created_at;
- фильтры как локальный UI-каркас;
- acknowledgement показывай только при capability, но в mock-режиме действие
  должно быть безопасным и локальным;
- никаких execution controls.

4. Events
- история событий;
- интерфейс SSE-клиента;
- bounded exponential backoff;
- остановка reconnect при unmount;
- дедупликация по стабильному event id;
- индикатор disconnected/reconnecting/live.

5. Signals
- inbox и status counters;
- detail page с lifecycle и risk rejection evidence;
- явно показывай, что approved_for_review не равно order approval;
- кнопок отправки ордера, автоторговли и обхода риска не существует;
- mutation-команды backend не реализуй, только типизированные интерфейсы и
  disabled UI shells, если они нужны для макета.

6. Connectors
- список, environment, health/status и capability matrix;
- не отображай и не запрашивай credential material;
- никакой формы секретов.

7. Data Quality
- policies, gaps, quarantine;
- freshness/stale markers;
- replay/recovery только как disabled capability-gated shell без вызова backend.

API-слой

- base URL поступает из runtime/env config, не захардкожен;
- AbortSignal поддерживается во всех read-запросах;
- единый тип ApiError;
- 401, 403, 404, 409, 422, 429 и 5xx получают разные безопасные сообщения;
- auth token передаётся извне через AuthContext и хранится только в памяти;
- localStorage/sessionStorage/cookies для токена не реализовывай;
- workspace context передаётся только способом, подтверждённым backend-кодом;
- если способ не подтверждён, создай интерфейс WorkspaceContextProvider и mock,
  но не выдумывай HTTP header;
- не логируй headers, токены, ответы с evidence или персональные данные;
- типы должны соответствовать фактическим Pydantic response models;
- Decimal-поля в transport layer моделируй строкой либо как подтверждённый JSON
  contract; не выполняй финансовые расчёты через JavaScript number.

Mock mode

- VITE_USE_MOCK_API=true включает полностью локальный mock adapter;
- fixtures детерминированы, timestamps содержат timezone;
- mock показывает normal, empty, partial, stale и error сценарии;
- mock не делает сеть и не содержит секретов;
- production build не должен случайно включать debug logging.

Качество UI

- семантический HTML;
- WCAG-friendly contrast и visible focus;
- aria-label только там, где обычной подписи недостаточно;
- таблицы имеют caption/headers;
- даты отображаются с явным UTC;
- layout работает на ширине 360 px и на desktop;
- prefers-reduced-motion соблюдается;
- никакой зависимости от цвета как единственного признака статуса.

Тесты

Обязательно реализуй и запусти:
- приложение рендерится в mock mode;
- все маршруты открываются;
- неизвестный маршрут даёт NotFound;
- смена workspace очищает query cache и не показывает старые данные;
- SSE client дедуплицирует событие и корректно прекращает reconnect;
- 403 не показывается как 500;
- Signals page не содержит order/execute/send order control;
- основные interactive controls доступны с клавиатуры;
- TypeScript typecheck, lint, unit tests и production build проходят.

Команды должны быть описаны в apps/web/README.md. Желательные scripts:
- dev
- build
- typecheck
- lint
- test
- check

Что запрещено

- менять любой файл вне apps/web/;
- менять backend, ORM, Alembic, RBAC, main.py или API;
- менять `docs/engineering-bible/` или статусы содержащихся там документов;
- менять root package.json, pyproject.toml, Docker, CI, README или документацию
  релиза;
- создавать endpoint или считать выдуманный endpoint существующим;
- реализовывать торговую стратегию, PnL, VaR, exposure или risk decision logic;
- отправлять ордера или создавать интерфейс обхода Risk Engine;
- хранить секреты;
- подключать аналитику, CDN, внешние шрифты или скрытую сеть;
- делать merge/rebase/push в main;
- заявлять production readiness.

Если фактический API неясен

Не угадывай. Оставь изолированный типизированный interface/adapter, используй mock
и добавь запись в apps/web/README.md в раздел Integration questions. Не меняй
backend ради удобства frontend.

Git и передача результата

Перед коммитом выполни:
1. git diff --name-only — все пути должны начинаться с apps/web/;
2. install с lock-файлом;
3. typecheck;
4. lint;
5. unit tests;
6. production build;
7. повторный git status, чтобы build artifacts и node_modules не попали в commit.
8. сверка реализованных решений с применимыми V06/V08 и перечень отклонений в
   `apps/web/README.md` без изменения самих стандартов.

Сделай один атомарный commit:
feat(web): scaffold live operations UI

Не создавай PR и не сливай ветку без команды владельца.

Обязательный архив передачи

После проверок сохрани все наработки в ZIP-архиве вне репозитория и вне worktree.
Имя архива:
`trade-signal-platform-hermes-live-operations-web-<short-commit>.zip`.
Если commit создать невозможно, вместо short commit используй `partial`.

Архив должен иметь следующую структуру:

handoff/
  HERMES_HANDOFF.md
  BASE_SHA.txt
  COMMIT_SHA.txt
  CHANGED_FILES.txt
  COMMANDS_RUN.txt
  TEST_RESULTS.txt
  BUILD_RESULTS.txt
  GIT_STATUS.txt
  BIBLE_CONFORMANCE.md
  hermes-live-operations-web.patch
  hermes-live-operations-web.bundle
  MANIFEST_SHA256.txt
apps/
  web/
    ... все исходники scaffold ...

Требования к архиву:

- `BASE_SHA.txt` содержит полный SHA, полученный командой
  `git rev-parse workstream-live-operations-base-v1^{commit}`, и перевод строки;
- `COMMIT_SHA.txt` содержит полный SHA созданного commit либо `none`;
- patch должен быть пригоден для проверки и переноса: при наличии commit создай
  его через `git format-patch --stdout workstream-live-operations-base-v1..HEAD`;
  при blocked/uncommitted состоянии используй
  `git diff --binary workstream-live-operations-base-v1`;
- Git bundle создаётся для ветки `hermes/live-operations-web`, если commit есть;
  если commit отсутствует, файл bundle не создавай, а явно зафиксируй это в
  `HERMES_HANDOFF.md`;
- `apps/web/` в архиве должен совпадать с передаваемым исходным деревом;
- не включай `.git`, `node_modules`, `dist`, `coverage`, кэши, временные файлы,
  `.env`, токены, credentials или иные секреты;
- `MANIFEST_SHA256.txt` содержит SHA-256 всех файлов архива, кроме самого manifest;
- после упаковки открой архив, проверь список файлов, распакуй его во временный
  каталог и сравни SHA-256 с manifest;
- вычисли отдельный SHA-256 самого ZIP и верни его в финальном отчёте;
- не удаляй ветку или worktree до подтверждения Codex, что архив принят и слит.

Даже при `STATUS: blocked` создай архив всех безопасно полученных наработок,
диагностик и незавершённого binary patch. Пустой архив или архив только с отчётом
без исходников неприемлем.

Финальный отчёт верни строго в формате:
STATUS: completed | blocked
BASE_SHA: <sha>
BRANCH: hermes/live-operations-web
COMMIT: <sha или none>
CHANGED_FILES: <список>
COMMANDS_RUN: <список>
TYPECHECK: passed | failed | not-run
LINT: passed | failed | not-run
TESTS: <точный результат>
BUILD: passed | failed | not-run
INTEGRATION_QUESTIONS: <список>
KNOWN_LIMITATIONS: <список>
BIBLE_CONFORMANCE: <применённые ID и отклонения>
ARCHIVE_PATH: <абсолютный путь к zip>
ARCHIVE_SHA256: <sha256>
ARCHIVE_CONTENTS_VERIFIED: yes | no
HANDOFF_TO_CODEX: review only; do not auto-merge
