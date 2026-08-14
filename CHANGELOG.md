# Changelog

Все заметные изменения KAgent фиксируются в этом файле.

Формат основан на Keep a Changelog. Проект следует Semantic Versioning после первого стабильного релиза.

## [Unreleased]

### Changed
- Gateway now preserves upstream `Content-Encoding`, allowing browsers to decode compressed Web responses instead of receiving a blank/unparseable page.
- Gateway startup now waits for a healthy Web service without a circular dependency, and Playwright waits for the actual login UI instead of only the Gateway liveness endpoint.
- Repository validation now scans tracked and non-ignored Git files instead of recursively traversing generated dependency/build trees.
- Hardened provider account pools: execution roles now select explicit pools, missing roles fail closed, operator endpoints require the internal service credential, and the public Gateway blocks the operator surface.
- Prepared the first server release candidate with guarded production Compose, Caddy TLS, loopback-only Gateway binding, restart policies, bounded logs, pinned infrastructure images, repeatable migrations, and full-state backup/restore tooling.
- Added real browser E2E coverage for the Web dashboard and made it a required CI and verification-status dependency.
- Gateway requests now receive peer connection metadata required by the rate limiter, preventing valid requests and the Compose liveness probe from failing with HTTP 500.
- Gateway runtime images now include the `wget` client required by the existing Compose healthcheck.
- CI now builds all seven service images on every push, pull request, and manual dispatch without running or publishing them, using scoped GitHub Actions layer caches.
- Docker builds now compile the gateway from real sources, install the control-plane within its pnpm workspace, and no longer require a missing web `public` directory.
- Added Account Pool and Model Registry Leases in Reasoning Engine (`ModelRegistry`). Implements per-request account leasing to prevent 429 rate limiting and quota exhaustion across parallel executions. Replaces single-key config with dynamic pool configuration. Includes API endpoints for manual account management.
- The replay evaluation suite now uses three runnable, deterministic stdlib repository snapshots with tracked response cassettes, immutable acceptance verifiers, empty-diff proofs, and adjacent-behavior mutation proofs; reports include zero-provider replay counters and recorded per-case cost/repair metrics.
- Verified capability status is generated deterministically from tracked successful `main` push evidence and published to the permanent `verification-state` branch without writing to `main`.
- CI now boots the complete Compose deployment, exercises the public Gateway workflow, verifies the private service perimeter, and preserves container diagnostics.
- Python CI now lints all Python test scopes and runs every unit test directory instead of a named-file allowlist.
- Refactored TOTP authentication to separate unit-testable policy from PostgreSQL persistence adapter, fixing cross-instance replay issues and atomic one-time challenges.

### Added
- Added a production preflight that rejects placeholder secrets, unsafe file permissions, public Gateway binding, invalid hostnames, and missing model-provider credentials.
- Agent Runtime unprivileged execution sandbox using bubblewrap (bwrap), enforcing workspace limits, preventing network access, and dropping secrets.
- Added recovery codes capability for TOTP, including generate and login endpoints, generating 10 hashed 128-bit codes with atomic revocation and secure double-use rejection.

- Исправлено поведение Pipeline и Reasoning Engine: ответы без 2xx считаются hard error без silent fallback (кроме fallback внутри Reasoning Engine, который работает по-прежнему), а failed TEST создает попытку REPAIR с последующим TEST, лимит исчерпания которого требует HUMAN_REQUIRED решения.

- Реализация Git-контура и контракта задачи (P3): изолированные рабочие пространства, атомарные коммиты с метаданными задачи, проверка разрешённых путей, идемпотентное создание Pull Request.
- Интеграция Pipeline с Reasoning Engine (P2): использование моделей для планирования и выполнения фаз `DEVELOP` и `REPAIR`, с подсчетом стоимости/токенов и строгими ограничениями по рабочим путям.
- Реализовано фактическое исполнение моделей в Reasoning Engine с отказоустойчивостью (fallback), подсчётом токенов/стоимости, кэшированием решений и поддержкой режимов live/record/replay через кассеты.
- Общая Python-библиотека событий с идемпотентным созданием потоков NATS JetStream, ограниченными попытками переподключения и интеграционным CI-тестом на настоящем брокере.
- Публикация `task.started`, `agent.started`, `agent.completed`, `artifact.created` и `task.failed` из Verified Coding Pipeline с версионированным конвертом событий.
- Контракт Reasoning Engine опубликован через публичную поверхность `@kagent/contracts`; добавлена проверка соответствия полей запроса и допустимых значений TypeScript-контракта Python-сервису.
- Разделы ТЗ 42–51: программная среда агента и Typed Host Bridge, субагенты и дерево сессии, долгоживущие сессии и ограниченный автономный режим, harness и навыки, приватность маршрутизации, версионирование протоколов, распределённое исполнение, интеграция с инфраструктурным слоем, операционные требования, согласование словаря.
- ADR-0017…ADR-0020 со статусом `proposed`: программная среда как поверхность инструментов, сессия как append-only дерево, приватность как ограничение маршрутизации, версионирование протоколов с согласованием возможностей.
- Этап 0.10 «Runtime and Distribution» в roadmap с песочницей как предусловием.
- Поддержка TOTP (двухфакторная аутентификация) реализована в TypeScript в control-plane, удален неиспользуемый Python модуль.
- GitManager с единым workspace для runtime и Git, path-filtered индексацией (allowed_paths/forbidden_paths), idempotent branch/commit/push через EffectLedger, TaskContract с проверкой лимитов. Интеграционные тесты с локальным bare remote.

- Разделы ТЗ 35–41: воспроизводимость выполнения, целостность верификации и интеграции, экономика выполнения и целостность эффектов, контракт человеческого решения, жизненный цикл контекста, память и границы данных, измеримость прогресса.
- ADR-0004…ADR-0016 со статусом `proposed`: кассеты и реплей запусков, целостность тестового оракула, двухфазный бюджетный ledger с автостопом, реестр промптов, eval-suite платформы и метрики автономности, merge queue и политика ветвления, ledger внешних эффектов, контракт человеческого решения, жизненный цикл контекста, кэш модельных вызовов, исполняемые уроки, изоляция личного контура, вычисляемый статус этапов.
- Индекс ADR в `docs/adr/README.md`.
- Этап 0.9 «Trust and Economics Foundation» в roadmap.

- Архитектурное решение Capability-first Reasoning Engine с бюджетным Router, режимами Economy/Balanced/Critical и оценкой по стоимости успешной задачи.
- Чистая monorepo-структура KAgent.
- Базовый Web-клиент.
- Каркас TypeScript Control Plane.
- Каркас Rust Gateway.
- Пакет versioned-контрактов.
- Docker Compose с PostgreSQL, NATS JetStream и MinIO.
- Архитектурные документы, ADR и threat model.
- Начальный тестовый и CI-каркас.
- Подключение ограничителя частоты запросов на gateway с настройкой через окружение.
- Job `python` в непрерывной интеграции.
- Модульные тесты control-plane и gateway.

### Changed

- Python-пакет Agent Runtime перенесён в импортируемый путь `services/agent_runtime`; Docker Compose, capability registry и обязательная Python CI-проверка используют тот же путь.
- Внутренние сервисы больше не публикуют HTTP-порты на хост; Gateway проксирует observability, а вызывающие действия runtime и pipeline требуют общий служебный секрет.
- Полное ТЗ приведено к разработке с чистого листа без этапа миграции legacy-кода.
- Definition of Done расширена проверками `test-diff-policy` и `mutation-check` и лимитами `unapproved_test_modifications` и `minimum_mutation_score`.
- В roadmap добавлено предупреждение, что статусы этапов 0.1–0.8 проставлены вручную и не подтверждены доказательствами выполнения.
- Ограничение раздела 10.2 смягчено: субагентам разрешена глубина 2 при резервировании бюджета поддерева у родителя.
- Таксономия типов узлов раздела 16.1 заменена таксономией раздела 48.1.
- Установка через передачу скачанного скрипта интерпретатору с правами суперпользователя запрещена; требуется версионированный релиз с проверкой контрольной суммы и подписи.
- Механика компактификации, атрибуция расхода субагентов и запрет платных вызовов провайдера в тестах внесены в ADR-0012, ADR-0006 и ADR-0004.

### Fixed

- Результаты и фактически выполненные команды job'ов CI теперь подаются в вычисляемый roadmap; подтверждённые возможности содержат ссылку на прогон и commit, а частично подтверждённые перечисляют недостающие доказательства.
- Исправлены синтаксические ошибки импорта (E401) в Reasoning Engine и логика обработки статуса `HUMAN_REQUIRED` при циклах восстановления в Pipeline Engine.
- Клиент событий теперь создаёт отсутствующий поток перед публикацией и durable-подпиской; недоступность брокера журналируется и не прерывает выполнение шага pipeline.
- Ошибка компиляции в `get_request_id`.
- Падение control-plane при старте из-за незаявленной зависимости логгера.
- Неработающее хеширование паролей из-за `require` в ESM-модуле.
- Отсутствие `pnpm-lock.yaml`.
- Пакет control-plane, выпадавший из корневой проверки типов.
- Проекты, задачи и журнал аудита переведены с in-memory хранилища на PostgreSQL: до этого всё терялось при перезапуске процесса, хотя этап 0.2 был отмечен выполненным.
- Журнал аудита стал по-настоящему неизменяемым. Отзыв прав у `PUBLIC` в миграции 001 не действовал на владельца таблицы, под которым работает приложение, поэтому `UPDATE` и `DELETE` по `audit_events` проходили. Миграция 003 добавляет триггеры, отклоняющие изменение, удаление и очистку для любой роли.

### Removed

- Satellite и федерация вынесены из плана в отдельное ТЗ до проработки модели владения и разрешения конфликтов.
