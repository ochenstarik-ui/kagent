# KAgent — полное техническое задание

**Версия:** 1.0  
**Дата:** 24 июля 2026 года  
**Статус:** базовая спецификация нового продукта  
**Тип продукта:** автономная мультиагентная платформа для разработки программного обеспечения и повседневной помощи  
**Принцип реализации:** собственная кодовая база без внедрения исходного кода сторонних проектов
**Основной репозиторий:** `https://github.com/ochenstarik-ui/kagent`  
**Роль документа:** главный источник продуктовых и архитектурных требований до декомпозиции на отдельные спецификации

---

## 1. Назначение документа

Документ определяет требования к созданию KAgent — самостоятельной локально разворачиваемой платформы, способной принимать идею пользователя, исследовать предметную область, формировать проверяемое техническое задание, проектировать архитектуру, автономно разрабатывать программное обеспечение, тестировать, проверять и готовить результат к развёртыванию.

Платформа также должна работать как персональный помощник через веб-интерфейс, desktop-клиент, Telegram и Android-приложение.

Документ является основным источником требований для проектирования и разработки. При конфликте с более ранними материалами настоящий документ имеет приоритет после его утверждения владельцем проекта.

---

## 2. Основные принципы

1. **Собственная реализация.** Код сторонних агентных платформ, workflow-систем и систем памяти не копируется и не включается в продукт.
2. **Локальный контроль.** Пользователь может развернуть всю платформу на собственном сервере.
3. **Провайдер-независимость.** Архитектура не зависит от одного поставщика LLM.
4. **Проверяемая автономность.** Агент действует самостоятельно в рамках заранее выданного контракта полномочий.
5. **Безопасность по умолчанию.** Опасные операции запрещены, пока не разрешены политикой.
6. **Доказуемый результат.** Завершение задачи подтверждается тестами, артефактами, журналами и независимой проверкой.
7. **Человеко-читаемая память.** Ключевые знания, решения и уроки доступны пользователю в открытом формате.
8. **Воспроизводимость.** Любое важное решение и эксперимент можно повторить по сохранённым входам.
9. **Ограниченность рассуждений.** Число циклов, стоимость, время и ресурсы всегда ограничены.
10. **Распределённость.** Несколько серверов объединяются в единый кластер с общей очередью и политиками.

---

## 3. Цели продукта

### 3.1. Главная цель

Создать автономного инженера программного обеспечения, который способен выполнить полный цикл:

```text
идея пользователя
→ исследование аналогов и рынка
→ выявление требований
→ улучшение идеи
→ техническое задание
→ архитектура
→ план реализации
→ разработка
→ тестирование
→ независимая проверка
→ исправления
→ сборка
→ подготовка развёртывания
→ отчёт и накопление опыта
```

### 3.2. Дополнительная цель

Создать персонального помощника, который может:

- работать с задачами и календарём;
- читать и готовить электронную почту;
- выполнять исследования;
- вести проектную память;
- готовить документы и отчёты;
- автоматизировать регулярные действия;
- взаимодействовать через Telegram, веб, desktop и Android.

### 3.3. Не цели первой версии

В первую версию не входят:

- копирование интерфейса или внутренней архитектуры сторонних продуктов;
- неконтролируемое выполнение любых shell-команд;
- самостоятельное расходование денег без лимитов;
- production-развёртывание без явной политики;
- хранение секретов в открытых конфигурационных файлах;
- неограниченная рекурсия субагентов;
- обучение собственной базовой LLM с нуля.

---

## 4. Пользовательские роли

### 4.1. Владелец

Имеет полный доступ к системе, политикам, секретам, серверам, бюджетам и аудиту.

### 4.2. Администратор

Управляет пользователями, узлами, развёртыванием и эксплуатацией, но не может менять защищённые политики владельца без отдельного разрешения.

### 4.3. Менеджер проекта

Создаёт проекты, задачи, контракты автономности и просматривает результаты.

### 4.4. Разработчик

Работает с репозиториями, заданиями, diff, тестами и артефактами.

### 4.5. Ревьюер

Имеет доступ к чтению кода, отчётам, тестам и замечаниям, но по умолчанию не может менять код.

### 4.6. Оператор

Запускает и останавливает задачи, наблюдает за очередью, инцидентами и узлами.

### 4.7. Наблюдатель

Имеет только доступ к просмотру разрешённых проектов и отчётов.

### 4.8. Сервисная идентичность агента

Каждый агент и worker получает собственную идентичность, набор прав, бюджет и журнал действий.

---

## 5. Каналы доступа

### 5.1. Web

Основной интерфейс управления:

- вход по email и паролю;
- обязательная поддержка 2FA;
- управление проектами;
- чат с агентом;
- просмотр workflow;
- просмотр памяти;
- задачи и запуски;
- история действий;
- управление моделями;
- кластер и серверы;
- секреты и политики;
- инциденты;
- отчёты и артефакты.

### 5.2. Desktop

Desktop-клиент должен:

- поддерживать Windows, macOS и Linux;
- подключаться к удалённому серверу KAgent;
- работать с локальными репозиториями через защищённый локальный мост;
- показывать уведомления;
- поддерживать безопасное локальное хранение токена;
- уметь запускать локальный worker;
- обеспечивать drag-and-drop файлов;
- поддерживать обновление приложения.

Рекомендуемая собственная реализация: Rust + Tauri + общий web frontend.

### 5.3. Telegram

Telegram-бот должен поддерживать:

- привязку аккаунта через одноразовый код;
- личные чаты;
- подтверждение критических операций;
- просмотр состояния задач;
- отправку файлов и голосовых сообщений;
- получение кратких отчётов;
- ограничение команд по ролям;
- отозвание устройства из web UI.

### 5.4. Android

Android-приложение должно поддерживать:

- Kotlin и Jetpack Compose;
- вход с 2FA;
- чат;
- проекты и задачи;
- push-уведомления;
- подтверждение операций;
- просмотр артефактов;
- голосовой ввод;
- локально зашифрованные токены;
- биометрическую разблокировку.

---

## 6. Архитектура верхнего уровня

```text
Clients
├── Web
├── Desktop
├── Android
└── Telegram
        │
        ▼
API Gateway
├── Authentication
├── Authorization
├── Rate limits
├── WebSocket/SSE
└── Audit entry
        │
        ▼
Control Plane
├── Project Service
├── Workflow Engine
├── Orchestrator
├── Policy Engine
├── Model Router
├── Memory Service
├── Credential Vault
├── Artifact Service
├── Incident Service
└── Cluster Scheduler
        │
        ▼
Execution Plane
├── Agent Runtime
├── Tool Runtime
├── Browser Workers
├── Coding Workers
├── GPU Workers
├── Test Workers
└── Deployment Workers
        │
        ▼
Storage Plane
├── PostgreSQL
├── Object Storage
├── Event/Task Queue
├── Search Index
├── Markdown Knowledge Store
└── Audit Log
```

---

## 7. Модульная структура продукта

Предлагаемая структура monorepo:

```text
kteam/
├── apps/
│   ├── web/
│   ├── desktop/
│   ├── android/
│   ├── gateway/
│   └── cli/
├── services/
│   ├── auth/
│   ├── projects/
│   ├── orchestrator/
│   ├── workflows/
│   ├── scheduler/
│   ├── model-router/
│   ├── memory/
│   ├── policies/
│   ├── credentials/
│   ├── artifacts/
│   ├── incidents/
│   └── notifications/
├── runtimes/
│   ├── agent-runtime/
│   ├── tool-runtime/
│   ├── sandbox/
│   └── worker/
├── packages/
│   ├── contracts/
│   ├── sdk-typescript/
│   ├── sdk-python/
│   ├── workflow-schema/
│   ├── policy-schema/
│   ├── ui-kit/
│   └── observability/
├── connectors/
│   ├── git/
│   ├── github/
│   ├── gitlab/
│   ├── telegram/
│   ├── email/
│   ├── calendar/
│   ├── browser/
│   ├── database/
│   └── mcp/
├── deploy/
│   ├── docker-compose/
│   ├── kubernetes/
│   ├── terraform/
│   └── scripts/
├── docs/
└── tests/
```

---

## 8. Проекты и рабочие пространства

### 8.1. Проект

Проект является основной единицей организации и содержит:

- описание и цели;
- репозитории;
- пользователей и роли;
- документацию;
- память;
- workflow;
- секреты;
- бюджеты;
- политики;
- задачи;
- запуски;
- артефакты;
- инциденты.

### 8.2. Рабочее пространство разработки

Каждая задача разработки выполняется в изолированном рабочем пространстве:

- отдельный Git worktree или clone;
- отдельная ветка;
- отдельная файловая песочница;
- отдельный каталог артефактов;
- отдельный журнал инструментальных действий;
- отдельные временные credentials;
- resource limits.

По умолчанию запрещено работать непосредственно в пользовательской основной ветке.

### 8.3. Контракт задачи

Перед запуском создаётся машиночитаемый контракт:

```yaml
id: task-123
project_id: project-1
objective: "Реализовать двухфакторную аутентификацию"
repository: "app"
base_branch: "main"

allowed_paths:
  - apps/web
  - services/auth
  - packages/contracts
  - tests

forbidden_paths:
  - deploy/production
  - secrets
  - .github/workflows

allowed_actions:
  - read_repository
  - edit_files
  - run_tests
  - create_branch
  - create_commit

approval_required:
  - change_production
  - publish_release
  - delete_data

limits:
  max_minutes: 120
  max_model_cost: 20
  max_changed_files: 30
  max_agent_turns: 80
  max_repair_cycles: 3
```

---

## 9. Автономный цикл создания программного обеспечения

### 9.1. Intake

Система принимает идею в свободной форме и создаёт структурированную карточку:

- проблема;
- целевая аудитория;
- ожидаемый результат;
- ограничения;
- данные;
- интеграции;
- платформа;
- бюджет;
- срок;
- требования безопасности.

Неясные детали могут быть заполнены обоснованными предположениями. Все предположения явно отмечаются.

### 9.2. Research

Research Agent:

- ищет аналоги;
- изучает официальную документацию;
- сравнивает функции;
- выявляет лицензии;
- оценивает риски;
- формирует список возможностей;
- сохраняет источники и даты;
- отделяет факты от предположений.

### 9.3. Product refinement

Product Agent предлагает улучшения:

- обязательные функции;
- отличительные функции;
- упрощения MVP;
- риски монетизации;
- эксплуатационные ограничения;
- варианты дальнейшего развития.

### 9.4. Hypothesis and evidence

Важные архитектурные решения оформляются как гипотезы:

```yaml
hypothesis_id: HYP-001
statement: "Использование NATS подходит для очереди задач"
assumptions: []
falsification_conditions: []
supporting_evidence: []
contradicting_evidence: []
status: proposed
```

Для каждой гипотезы собираются подтверждающие и опровергающие данные.

### 9.5. Challenge

Challenger Agent пытается обнаружить:

- непроверенные допущения;
- пропущенные требования;
- угрозы безопасности;
- проблемы масштабирования;
- эксплуатационные сложности;
- несоответствия бюджета;
- риск vendor lock-in;
- неполную Definition of Done.

Число раундов ограничено. Повторные возражения не принимаются без новых данных.

### 9.6. Experiment

Если решение нельзя принять по документации, создаётся ограниченный эксперимент:

- цель;
- варианты;
- фиксированные входы;
- метрики;
- бюджет;
- критерий победы;
- stop conditions;
- reproducibility key.

### 9.7. Specification

Specification Agent создаёт:

- продуктовые требования;
- функциональные требования;
- нефункциональные требования;
- архитектуру;
- модель данных;
- API;
- безопасность;
- сценарии использования;
- тестовую стратегию;
- этапы реализации;
- критерии приёмки.

### 9.8. Planning

Planner создаёт dependency graph задач, определяет параллельные workstream и назначает роли.

### 9.9. Implementation

Developer Agents выполняют задачи в изолированных worktree. Каждый агент получает минимально необходимый контекст и права.

### 9.10. Verification

Проверка состоит минимум из:

1. автоматических тестов;
2. статического анализа;
3. проверки безопасности;
4. независимого code review;
5. проверки соответствия спецификации;
6. проверки изменённых файлов и разрешённых путей.

### 9.11. Repair

Блокирующие замечания запускают ограниченный цикл исправлений. После исчерпания лимита задача получает статус `needs-human-decision`.

### 9.12. Completion

Задача закрывается только при выполнении исполняемой Definition of Done и сохранении доказательств.

---

## 10. Мультиагентная модель

### 10.1. Системные роли

- Intake Agent;
- Research Agent;
- Product Agent;
- Requirements Agent;
- Architect Agent;
- Planner Agent;
- Developer Agent;
- Test Agent;
- Code Reviewer;
- Security Reviewer;
- Specification Verifier;
- Challenger Agent;
- Release Agent;
- Documentation Agent;
- Personal Assistant Agent.

### 10.2. Ограничения

- субагенты не создают субагентов напрямую;
- дерево агентов создаёт только Orchestrator;
- каждый агент имеет лимиты времени, токенов, стоимости и инструментов;
- reviewer по умолчанию имеет read-only доступ;
- критические роли желательно назначать разным моделям;
- все сообщения между агентами сохраняются как структурированные события;
- секреты не включаются в контекст модели.

### 10.3. Передача результатов

Результаты передаются через типизированные контракты, а не только через свободный текст:

```json
{
  "status": "completed",
  "summary": "Добавлена поддержка TOTP",
  "artifacts": ["test-report.json", "changes.patch"],
  "findings": [],
  "risks": [],
  "confidence": 0.91
}
```

---

## 11. Workflow Engine

### 11.1. Назначение

Собственный workflow engine управляет многошаговыми процессами и не зависит от n8n или другой внешней системы.

### 11.2. Типы узлов

- trigger;
- agent;
- tool;
- condition;
- switch;
- parallel;
- join;
- loop;
- retry;
- wait;
- approval;
- policy gate;
- budget gate;
- memory read/write;
- subworkflow;
- notification;
- artifact validation.

### 11.3. Требования

- версия workflow;
- визуальное и YAML-представление;
- типизированные входы и выходы;
- checkpoints;
- idempotency;
- повтор с ошибочного узла;
- замораживание успешных узлов;
- timeout;
- retry policy;
- compensation actions;
- cancellation;
- audit;
- шаблоны;
- импорт и экспорт;
- dry-run.

### 11.4. Пример

```yaml
workflow:
  id: software-build
  version: 1

nodes:
  - id: intake
    type: agent
    role: intake

  - id: research
    type: agent
    role: researcher

  - id: spec
    type: agent
    role: requirements

  - id: approval
    type: approval
    policy: specification

  - id: implementation
    type: subworkflow
    workflow: verified-development

edges:
  - from: intake
    to: research
  - from: research
    to: spec
  - from: spec
    to: approval
  - from: approval
    to: implementation
    condition: approved
```

---

## 12. Память и знания

### 12.1. Слои памяти

1. системные политики;
2. North Star пользователя;
3. профиль пользователя;
4. память проекта;
5. решения и ADR;
6. задачи и запуски;
7. уроки и инциденты;
8. кратковременный контекст сессии;
9. архивные журналы.

### 12.2. Форматы хранения

- Markdown — долговечные человеко-читаемые знания;
- PostgreSQL — сущности и состояние;
- поисковый индекс — полнотекстовый и семантический поиск;
- object storage — большие файлы;
- append-only audit store — критические события.

### 12.3. Статусы знания

- raw;
- candidate;
- active;
- stale;
- rejected;
- superseded.

### 12.4. Метаданные

```yaml
id:
title:
type:
status:
source:
source_hash:
created_at:
reviewed_at:
reviewed_by:
confidence:
scope:
supersedes:
links:
```

### 12.5. Контекстные пакеты

Context Builder формирует пакет под конкретную роль. Пакет содержит:

- контракт задачи;
- соответствующие документы;
- актуальные решения;
- разрешённые инструменты;
- ограничения;
- список источников;
- размер в токенах;
- контрольную сумму.

Полное хранилище памяти никогда не загружается в контекст автоматически.

### 12.6. Поиск

Последовательность fallback:

```text
hybrid semantic search
→ vector search
→ full-text/BM25
→ metadata filtering
→ grep/ripgrep
→ direct file traversal
```

### 12.7. Граф знаний

Поддерживаются связи:

- основано на;
- подтверждает;
- противоречит;
- отменяет;
- относится к;
- реализует;
- обнаружено в;
- исправлено в;
- зависит от;
- применимо к.

---

## 13. Model Router

### 13.1. Назначение

Model Router выбирает модель по требуемой способности, качеству, приватности, стоимости и доступности.

### 13.2. Требования задания

```yaml
capability: code-review
minimum_context: 100000
privacy: private-or-approved-cloud
quality: high
max_cost: 3.00
latency: normal
fallback_allowed: true
```

### 13.3. Поставщики

- OpenAI-compatible API;
- Anthropic-compatible adapter;
- Google-compatible adapter;
- локальные OpenAI-compatible endpoints;
- собственные adapters через SDK.

### 13.4. Квалификация моделей

Локальные модели проходят eval suite и получают уровни:

```text
unverified
→ classification-only
→ research
→ code-assistant
→ code-author
→ reviewer
→ trusted-critical
```

### 13.5. Бюджетные профили

- economy;
- balanced;
- quality;
- critical.

### 13.6. Политика выхода данных

Перед облачным запросом проверяется тип данных:

```yaml
data_egress:
  public_docs: allowed
  source_code: approved_providers_only
  personal_email: local_only
  credentials: forbidden
  production_database: forbidden
```

---

## 14. Инструменты и connectors

### 14.1. Базовые connectors

- filesystem;
- Git;
- GitHub;
- GitLab;
- shell;
- browser;
- HTTP;
- PostgreSQL;
- SQLite;
- Docker;
- Kubernetes;
- email;
- calendar;
- Telegram;
- object storage;
- MCP client.

### 14.2. Tool contract

Каждый инструмент описывает:

- schema входа;
- schema выхода;
- уровень риска;
- необходимые permissions;
- возможность отката;
- timeout;
- idempotency;
- тип данных;
- audit policy.

### 14.3. Shell

Предпочтительная форма вызова:

```json
["python", "-m", "pytest", "-q"]
```

По умолчанию:

- `shell=false`;
- executable allowlist;
- запрещены `sudo`, `mount`, `ssh`, `scp`;
- запрещены shell operators без отдельного разрешения;
- ограничены CPU, RAM, процессы и время;
- файловая система ограничена workspace.

### 14.4. Browser

Browser worker должен:

- работать в изолированном профиле;
- маркировать внешнее содержимое как недоверенное;
- ограничивать загрузки;
- блокировать доступ к локальной сети по политике;
- сохранять URL, timestamp и извлечённые фрагменты;
- защищаться от prompt injection.

---

## 15. Безопасность

### 15.1. Аутентификация

- email и пароль;
- Argon2id;
- TOTP;
- recovery codes;
- optional WebAuthn/passkeys;
- управление сессиями;
- отзыв устройств;
- уведомление о новых входах;
- rate limiting;
- блокировка bruteforce.

### 15.2. Авторизация

- RBAC;
- project scopes;
- resource permissions;
- сервисные идентичности;
- временные токены;
- deny-by-default;
- policy evaluation для каждого критического действия.

### 15.3. Credential Vault

- шифрование at rest;
- envelope encryption;
- master key вне базы данных;
- project isolation;
- short-lived injection;
- rotation;
- masking;
- audit;
- запрет передачи в LLM context.

### 15.4. Input Firewall

Все внешние входы проходят:

- Unicode normalization;
- удаление невидимых символов;
- content classification;
- secret detection;
- prompt injection detection;
- source trust scoring;
- quarantine;
- отделение инструкций от данных.

### 15.5. Sandbox

Минимальные требования:

- rootless containers;
- seccomp;
- AppArmor/SELinux при наличии;
- read-only base filesystem;
- writable workspace volume;
- network policy;
- process limits;
- CPU/RAM limits;
- no privileged mode;
- no host Docker socket по умолчанию.

### 15.6. Supply chain

- lockfiles;
- dependency pinning;
- SBOM;
- vulnerability scanning;
- image signatures;
- checksum verification;
- protected release pipeline;
- запрет автоматической установки непроверенных skills и plugins.

### 15.7. Tamper-evident audit

Критические события связываются hash chain:

```text
event_n.hash = SHA256(event_n.data + event_n.previous_hash)
```

Проверяются:

- изменение политики;
- выдача permissions;
- использование секрета;
- production action;
- изменение памяти;
- утверждение спецификации;
- выпуск релиза.

---

## 16. Распределённый кластер

### 16.1. Типы узлов

- controller;
- general worker;
- coding worker;
- browser worker;
- GPU worker;
- storage node;
- deployment worker.

### 16.2. Регистрация узла

Новый узел подключается по одноразовому join token, после чего получает собственный сертификат и identity.

### 16.3. Scheduler

Учитывает:

- capabilities;
- CPU и RAM;
- GPU и VRAM;
- локальность данных;
- privacy zone;
- установленные инструменты;
- состояние узла;
- стоимость;
- текущую очередь;
- affinity и anti-affinity.

### 16.4. Lease и heartbeat

Каждая задача получает lease. Worker отправляет heartbeat. При потере worker задача возвращается в очередь после безопасного timeout или восстанавливается из checkpoint.

### 16.5. Отказоустойчивость

- повторяемые задания должны быть idempotent;
- checkpoints сохраняются в object storage;
- controller state хранится в PostgreSQL;
- очередь поддерживает durable delivery;
- orphan tasks обнаруживаются supervisor;
- повтор ограничен политикой.

### 16.6. Сеть

- TLS между всеми узлами;
- mTLS для служебных соединений;
- возможность private overlay network;
- network zones;
- запрет доверия только по IP;
- ротация сертификатов.

---

## 17. Supervisors и инциденты

### 17.1. Runtime Supervisor

Обнаруживает:

- зависшие задания;
- потерянные leases;
- retry storm;
- циклы;
- отсутствие heartbeat;
- рост логов;
- превышение времени;
- превышение бюджета.

### 17.2. Security Supervisor

Проверяет целостность:

- политик;
- auth-конфигурации;
- sandbox;
- tool allowlists;
- системных инструкций;
- модулей credential access.

При критическом нарушении переводит систему в read-only.

### 17.3. Hardware Supervisor

Контролирует:

- CPU;
- load average;
- RAM;
- swap;
- disk space;
- inode;
- GPU;
- VRAM;
- температуру;
- сеть.

### 17.4. Incident model

```yaml
incident_id:
type:
severity:
first_seen:
last_seen:
occurrence_count:
affected_nodes:
affected_tasks:
state:
recommended_action:
```

Статусы:

- open;
- acknowledged;
- mitigated;
- resolved;
- ignored.

---

## 18. API

### 18.1. Стиль

- REST для CRUD и административных операций;
- WebSocket или SSE для событий и потоковых ответов;
- internal RPC для высоконагруженных service-to-service операций;
- OpenAPI для публичного API;
- versioned API.

### 18.2. Основные ресурсы

```text
/api/v1/auth
/api/v1/users
/api/v1/projects
/api/v1/repositories
/api/v1/tasks
/api/v1/runs
/api/v1/agents
/api/v1/workflows
/api/v1/models
/api/v1/memory
/api/v1/artifacts
/api/v1/secrets
/api/v1/policies
/api/v1/nodes
/api/v1/incidents
/api/v1/audit
```

### 18.3. Webhooks

- подписанные запросы;
- timestamp;
- nonce;
- retry;
- delivery log;
- replay protection;
- per-project secrets.

---

## 19. Модель данных

Основные сущности:

- User;
- Organization;
- Membership;
- Project;
- Repository;
- Task;
- TaskContract;
- Workflow;
- WorkflowVersion;
- WorkflowRun;
- NodeRun;
- AgentIdentity;
- AgentRun;
- ModelProvider;
- ModelProfile;
- WorkerNode;
- Lease;
- Artifact;
- KnowledgeItem;
- KnowledgeLink;
- DecisionRecord;
- Hypothesis;
- Evidence;
- Experiment;
- Policy;
- CredentialReference;
- Incident;
- AuditEvent;
- Notification;
- ApprovalRequest.

Все сущности содержат UUID, timestamps, owner scope и версию для optimistic concurrency.

---

## 20. Пользовательский интерфейс

### 20.1. Главный экран

- текущие проекты;
- активные задачи;
- состояние кластера;
- расходы;
- предупреждения;
- последние артефакты;
- быстрый чат.

### 20.2. Экран проекта

Вкладки:

- Overview;
- Chat;
- Tasks;
- Repositories;
- Specification;
- Workflows;
- Memory;
- Decisions;
- Runs;
- Artifacts;
- Policies;
- Settings.

### 20.3. Workflow Canvas

- drag-and-drop nodes;
- connection validation;
- zoom и mini-map;
- версия workflow;
- diff версий;
- запуск выбранной ветки;
- отображение статуса узлов;
- просмотр входа и выхода;
- replay;
- export YAML.

### 20.4. Run Timeline

Для каждого запуска:

- этапы;
- агенты;
- модели;
- tool calls;
- стоимость;
- длительность;
- логи;
- checkpoints;
- артефакты;
- причины решений;
- замечания reviewers.

---

## 21. Наблюдаемость

- OpenTelemetry;
- structured logs;
- metrics;
- traces;
- correlation IDs;
- dashboards;
- alerting;
- cost metrics;
- model latency;
- queue depth;
- token consumption;
- task success rate;
- retry rate;
- incident rate;
- worker utilization.

Логи не должны содержать пароли, токены, секреты или полные персональные данные.

---

## 22. Развёртывание

### 22.1. Single-server

Команда первого запуска:

```bash
curl -fsSL https://example.invalid/kteam/install.sh | sh
```

Фактический production installer должен:

- проверить систему;
- установить или проверить Docker;
- сгенерировать секреты;
- создать volumes;
- поднять сервисы;
- выполнить миграции;
- вывести URL и одноразовый setup token;
- запустить health checks.

### 22.2. Docker Compose

Минимальный набор:

- gateway;
- web;
- control-plane;
- worker;
- PostgreSQL;
- task/event broker;
- object storage;
- reverse proxy.

### 22.3. Kubernetes

Поддержка:

- Helm chart;
- horizontal autoscaling;
- secrets integration;
- network policies;
- persistent volumes;
- pod disruption budgets;
- rolling updates.

### 22.4. CLI

```text
kteam install
kteam onboard
kteam login
kteam doctor
kteam status
kteam project create
kteam task run
kteam workflow validate
kteam node join
kteam backup
kteam restore
kteam upgrade
```

Daemon: `kteamd`.

### 22.5. Backup

Backup содержит:

- PostgreSQL dump;
- encrypted credential metadata;
- Markdown knowledge;
- object storage manifest;
- workflow definitions;
- policies;
- audit checkpoint;
- version manifest.

Restore обязательно проверяется автоматическим тестом.

---

## 23. Технологический стек

Предпочтительная стартовая комбинация:

- frontend: Next.js + TypeScript;
- desktop: Tauri + Rust;
- Android: Kotlin + Compose;
- gateway и security-sensitive runtime: Rust;
- control-plane services: TypeScript или Rust;
- worker runtime: Rust;
- Python SDK для data/ML jobs;
- PostgreSQL;
- NATS JetStream или собственно выбранный после benchmark broker adapter;
- S3-compatible object storage;
- OpenTelemetry;
- Docker rootless;
- Kubernetes для cluster deployment.

Окончательный выбор очереди, search engine и vector store принимается через воспроизводимый benchmark.

---

## 24. Качество кода

- strict TypeScript;
- Rust clippy и fmt;
- unit tests;
- integration tests;
- contract tests;
- end-to-end tests;
- migration tests;
- security tests;
- deterministic test fixtures;
- linting;
- dependency scanning;
- minimum coverage targets по критичности;
- запрет merge при критических ошибках.

---

## 25. Definition of Done

Пример исполняемой политики:

```yaml
definition_of_done:
  required_checks:
    - unit-tests
    - integration-tests
    - lint
    - typecheck
    - security-scan
    - specification-verification

  required_artifacts:
    - change-summary
    - test-report
    - reviewer-report
    - agent-changelog

  limits:
    critical_vulnerabilities: 0
    high_vulnerabilities: 0
    test_failures: 0
    forbidden_path_changes: 0
```

---

## 26. Документация

Обязательные документы:

- PRODUCT_SPEC.md;
- ARCHITECTURE.md;
- THREAT_MODEL.md;
- SECURITY_POLICY.md;
- API.md;
- DATA_MODEL.md;
- DEPLOYMENT.md;
- OPERATIONS.md;
- BACKUP_RESTORE.md;
- CONTRIBUTING.md;
- AGENT_GUIDE.md;
- AGENT_CHANGELOG.md;
- CHANGELOG.md;
- ADR directory.

Приоритет источников:

1. утверждённое ТЗ;
2. security policy;
3. ADR;
4. API contracts и schemas;
5. активные task contracts;
6. operational docs;
7. README;
8. комментарии в коде;
9. история чата.

---

## 27. Этапы реализации

### Этап 0. Foundation bootstrap

- аудит текущего репозитория;
- фиксация полезных собственных компонентов;
- переименование продукта;
- создание новой структуры;
- отделение legacy-кода;
- базовый threat model;
- CI.

### Этап 1. Foundation

- auth с email/password/TOTP;
- проекты;
- PostgreSQL;
- Gateway;
- базовый web UI;
- CLI;
- audit events;
- credential vault;
- Docker Compose.

### Этап 2. Agent runtime

- model adapters;
- model router;
- tool contracts;
- sandbox;
- task contracts;
- single-agent execution;
- artifacts;
- streaming output.

### Этап 3. Autonomous coding MVP

- Git connector;
- worktree manager;
- planner;
- developer;
- test runner;
- reviewer;
- repair loop;
- Definition of Done;
- full run timeline.

### Этап 4. Memory

- Markdown knowledge store;
- North Star;
- project memory;
- search;
- context builder;
- decisions;
- evidence;
- knowledge validation;
- session lifecycle hooks.

### Этап 5. Workflow engine

- workflow schema;
- scheduler;
- node execution;
- retries;
- checkpoints;
- approvals;
- subworkflows;
- YAML editor;
- basic visual canvas.

### Этап 6. Distributed execution

- node enrollment;
- mTLS;
- worker capabilities;
- leases;
- heartbeat;
- cluster scheduler;
- GPU workers;
- supervisors;
- failover.

### Этап 7. Clients and channels

- Telegram;
- desktop;
- Android;
- notifications;
- local desktop worker.

### Этап 8. Production hardening

- Kubernetes;
- HA;
- backup/restore testing;
- supply-chain security;
- load tests;
- penetration testing;
- release signing;
- upgrade/rollback.

---

## 28. MVP

MVP считается готовым, когда пользователь может:

1. развернуть KAgent на одном сервере через Docker Compose;
2. создать владельца с TOTP;
3. создать проект;
4. подключить Git-репозиторий;
5. подключить минимум двух поставщиков моделей;
6. описать задачу разработки в чате;
7. получить технический план;
8. разрешить автономную реализацию;
9. получить отдельную ветку с изменениями;
10. увидеть выполненные тесты;
11. получить независимый review;
12. увидеть полный журнал действий и расходов;
13. скачать артефакты;
14. остановить выполнение аварийной кнопкой;
15. восстановить систему из backup.

---

## 29. Критерии приёмки первой production-версии

### Функциональные

- web, desktop, Telegram и Android работают с одним сервером;
- 2FA обязательна для privileged roles;
- задачи выполняются через workflow engine;
- coding pipeline создаёт отдельный worktree и ветку;
- reviewer не может менять код без отдельного права;
- cluster поддерживает минимум три worker-узла;
- потеря worker не приводит к потере состояния задачи;
- память сохраняется между сессиями;
- пользователь видит источники и причины ключевых решений;
- production actions контролируются approval policy.

### Безопасность

- отсутствуют plaintext secrets;
- запрещён privileged container mode;
- все service-to-service соединения защищены;
- проведён внешний security review;
- prompt injection tests включены в CI;
- критические audit events защищены hash chain;
- можно отозвать любую пользовательскую или сервисную сессию.

### Надёжность

- backup и restore проходят автоматический сценарий;
- после перезапуска controller незавершённые задачи восстанавливаются;
- retry storm блокируется;
- заполнение диска создаёт инцидент и останавливает новые тяжёлые задачи;
- обновление поддерживает rollback.

### Производительность

Целевые значения уточняются benchmark, но baseline:

- API p95 менее 500 мс для обычных CRUD-операций;
- доставка событий UI менее 2 секунд;
- восстановление lease после потери worker менее 60 секунд;
- поддержка минимум 100 параллельных лёгких задач на кластерной конфигурации;
- отсутствие загрузки всей памяти проекта в LLM context.

---

## 30. Создание проекта с чистого листа

KAgent создаётся как новый самостоятельный продукт в отдельном репозитории `ochenstarik-ui/kagent`.

Старые проекты и сторонние решения могут использоваться только как источники общих идей, требований и накопленного опыта. Их исходный код не переносится в KAgent автоматически.

Порядок запуска разработки:

1. утвердить настоящее техническое задание как основной источник требований;
2. создать чистую monorepo-структуру;
3. зафиксировать архитектурные контракты и ADR;
4. реализовать минимальное ядро без зависимости от старых runtime-компонентов;
5. создавать каждый ключевой модуль заново с собственными тестами;
6. вести `CHANGELOG.md` для пользователя и `AGENT_CHANGELOG.md` для агентов;
7. проверять лицензии всех добавляемых зависимостей;
8. сохранять воспроизводимые сборки и контрольные суммы релизных архивов;
9. выполнять изменения через отдельные задачи, ветки и проверяемые результаты;
10. накапливать всю дальнейшую разработку в репозитории `kagent`.


---

## 31. Правила независимости от стороннего кода

1. Не копировать исходные файлы сторонних проектов.
2. Не копировать UI один в один.
3. Не использовать названия, логотипы и защищённые элементы сторонних продуктов.
4. Любая новая зависимость проходит лицензионную проверку.
5. Предпочтительны permissive licenses: MIT, Apache-2.0, BSD.
6. Source-available компоненты не включаются в ядро без юридического анализа.
7. Внешние сервисы подключаются через официальные API и адаптеры.
8. Архитектурные идеи описываются собственными контрактами и реализуются заново.
9. Для каждой зависимости ведётся SBOM и license inventory.
10. Все ключевые компоненты KAgent должны иметь собственные тесты и документацию.

---

## 32. Итоговая концепция

KAgent должен стать управляемой системой автономного исполнения, а не просто чат-ботом с доступом к shell.

Его отличительные свойства:

- полноценный цикл от идеи до проверенного программного продукта;
- договорная автономность без постоянных подтверждений;
- собственный workflow engine;
- собственная долговременная память;
- доказательства и опровержение решений;
- независимый review;
- безопасные sandbox и инструменты;
- распределённый кластер локальных и облачных исполнителей;
- web, desktop, Telegram и Android;
- прозрачные бюджеты и причины решений;
- человеко-читаемая память;
- аварийная остановка;
- воспроизводимые эксперименты;
- отсутствие внедрения чужого исходного кода.

---

## 33. Решение о начале разработки

Разработка начинается с Этапа 0 — Foundation bootstrap.

Первый исполняемый инкремент должен:

- создать чистую monorepo-структуру;
- зафиксировать ADR по структуре и границам модулей;
- определить versioned-контракты задач, событий и артефактов;
- добавить минимальные каркасы Web, Control Plane и Gateway;
- добавить локальную инфраструктуру PostgreSQL, NATS и S3-compatible storage;
- включить проверки форматирования, типов и тестов;
- вести `CHANGELOG.md` и `AGENT_CHANGELOG.md` с первого изменения.

После прохождения проверок начинается Этап 1 — Foundation.


---

## 34. Capability-first Reasoning Engine

### 34.1. Основной принцип

KAgent не должен зависеть от конкретного поставщика или семейства моделей.

Агенты запрашивают не имя модели, а требуемую способность:

- архитектурное проектирование;
- программирование;
- проверка кода;
- анализ безопасности;
- планирование;
- исследование;
- работа с документами;
- мультимодальный анализ;
- использование инструментов;
- локальная обработка конфиденциальных данных.

Reasoning Engine выбирает исполнителя через Model Registry, Capability Registry и Policy Router.

### 34.2. Model Adapter API

Каждый провайдер подключается через унифицированный адаптер.

Адаптер обязан предоставлять:

- идентичность провайдера, модели, версии и конфигурации;
- перечень поддерживаемых возможностей;
- ограничения контекста и инструментов;
- потоковый и обычный режимы ответа;
- structured output при наличии;
- usage accounting;
- нормализованные ошибки;
- отмену;
- таймауты;
- health и availability status.

Провайдерские SDK и названия не должны проникать в доменную логику агентов.

### 34.3. Capability Registry

Реестр хранит как заявленные характеристики, так и измеренные свойства модели:

- качество по категориям задач;
- надёжность;
- стоимость успешного результата;
- скорость;
- точность tool calling;
- способность работать с длинным контекстом;
- мультимодальность;
- приватность и место выполнения;
- текущая доступность;
- доверительный уровень статистики.

Профиль должен учитывать не только модель, но и её версию, режим рассуждения, параметры, квантование и набор инструментов.

### 34.4. Экономная оценка моделей

KAgent не проводит постоянный полный турнир моделей.

Основная статистика собирается как побочный результат обычной работы:

1. Router выбирает модель.
2. Модель выполняет пользовательскую задачу.
3. Стандартные проверки оценивают результат.
4. Usage и outcome telemetry записываются в профиль.
5. Router обновляет статистику для будущих задач.

Для программной разработки используются уже необходимые проверки:

- сборка;
- тесты;
- линтеры;
- статический анализ;
- security scanners;
- проверка контрактов;
- критерии приёмки;
- количество циклов исправления.

Отдельные тесты допускаются только при подключении новой модели, смене версии, деградации качества, низкой уверенности Router или для критических задач.

### 34.5. Shadow Mode

Shadow Mode запускает дополнительную модель параллельно, но не использует её результат как основной.

Он должен:

- быть выключен по умолчанию в Economy;
- использовать малую настраиваемую выборку в Balanced;
- иметь отдельный лимит расходов;
- автоматически уменьшаться или выключаться после накопления достаточной статистики;
- не запускаться при строгих ограничениях приватности без разрешения политики.

### 34.6. Режимы работы

#### Economy

- одна недорогая подходящая модель;
- отсутствие consensus;
- отсутствие shadow по умолчанию;
- переход к более сильной модели только после объективной неудачи.

#### Balanced

- выбор по исторической стоимости успешного результата;
- редкое shadow-тестирование;
- reviewer только при необходимости;
- автоматическая эскалация при низкой уверенности.

#### Critical

- несколько независимых кандидатов при необходимости;
- независимый reviewer;
- усиленные проверки;
- повышенный, но всё равно жёстко ограниченный бюджет.

### 34.7. Бюджеты

Каждая задача должна иметь ограничения:

```yaml
reasoning_budget:
  max_cost_usd: 0.20
  max_input_tokens: 100000
  max_output_tokens: 20000
  max_model_calls: 3
  max_candidates: 1
  max_repair_attempts: 2
  max_reviewer_calls: 0
  allow_shadow: false
  allow_consensus: false
```

Перед превышением жёсткого лимита выполнение останавливается или запрашивает подтверждение пользователя.

### 34.8. Стоимость успешной задачи

Основная экономическая метрика:

```text
cost_per_successful_task =
общая стоимость всех попыток / число успешно завершённых задач
```

Дешёвая модель, требующая многих повторов, может оказаться дороже сильной модели, решающей задачу с первой попытки.

### 34.9. Приоритет доказательств

Результаты моделей оцениваются в следующем порядке:

1. автоматические тесты и критерии приёмки;
2. компиляция и статический анализ;
3. проверки безопасности и политик;
4. соответствие контрактам;
5. независимое ревью;
6. обратная связь пользователя;
7. субъективная оценка LLM-судьи.

Модель не может сама объявить собственное решение лучшим.

### 34.10. Версионирование профилей

Каждая комбинация считается отдельным исполнителем:

```text
provider / model / version / configuration
```

После обновления версии или существенного изменения конфигурации новый профиль проходит консервативную переоценку и не наследует полностью рейтинг старого профиля.

### 34.11. Целевая схема

```text
Task
  ↓
Task Classifier
  ↓
Capability Requirements
  ↓
Budget and Privacy Policy
  ↓
Model and Capability Registry
  ↓
Historical Outcome Statistics
  ↓
Policy Router
  ↓
Selected Model or Model Team
  ↓
Execution
  ↓
Objective Verification
  ↓
Usage and Outcome Telemetry
  ↓
Capability Profile Update
```

---

## 35. Воспроизводимость выполнения

### 35.1. Принцип

Автономный запуск считается воспроизводимым, если его можно повторить без обращения к поставщику модели и получить тот же результат. Невоспроизводимый запуск нельзя ни протестировать, ни расследовать, ни сравнить с альтернативой.

Реплей workflow на канве повторяет топологию графа, но не поведение модели. Для поведения требуется отдельный механизм.

### 35.2. Кассеты модельных вызовов

Каждый вызов модели записывается как неизменяемая запись:

```yaml
run_id: run-88
step_id: step-12
agent_role: code-reviewer
attempt: 1
prompt_hash: sha256:...
prompt_registry_version: code-reviewer@2.3.0
model_id: provider/model
model_profile_version: 2026-07-30
sampling:
  temperature: 0.2
  seed: 4711
request: {...}
response: {...}
tokens_input: 18422
tokens_output: 1130
cost_usd: 0.0714
latency_ms: 6120
context_package_checksum: sha256:...
```

Кассеты хранятся в object storage как неизменяемые объекты, ссылаются из Run Timeline и audit log, наследуют privacy class проекта и подчиняются политике выхода данных.

Секреты в кассеты не попадают: применяются те же правила маскирования, что и для логов.

### 35.3. Режимы выполнения

- `live` — вызов поставщика с записью кассеты;
- `record` — как `live`, но запуск падает при попытке перезаписать существующую кассету;
- `replay` — ответы разрешаются только из кассет, обращение к поставщику запрещено.

Ключ разрешения: `(run_id, step_id, attempt)` для точного реплея и `(agent_role, prompt_hash)` для фикстур. Отсутствие кассеты в режиме `replay` — жёсткая ошибка. Тихий переход к живому вызову запрещён.

### 35.4. Реестр промптов

Инструкции ролей являются версионируемым артефактом, а не строковой константой в коде.

Манифест промпта:

```yaml
prompt_id: code-reviewer
version: 2.3.0
content_hash: sha256:...
inputs: [task_contract, diff, test_report, project_policies]
output_contract: reviewer-report@1
compatible_capabilities: [code-review, reasoning]
changelog: "Ужесточена проверка изменений существующих тестов"
```

Правила:

- runtime получает промпты только через реестр;
- каждый шаг запуска фиксирует `prompt_id` и версию;
- изменение промпта — это изменение поведения системы и проходит через eval-suite;
- предыдущие версии остаются разрешимыми, иначе записанные запуски перестают быть воспроизводимыми;
- две версии роли могут работать параллельно только в рамках явного эксперимента с фиксированной долей трафика и сроком решения.

### 35.5. Требования

- сборка контекстного пакета детерминирована при одинаковых входах;
- кассеты имеют политику хранения и удаляются вместе с проектом;
- реплей запуска доступен оператору из Run Timeline одним действием;
- регрессионные прогоны пайплайна в CI выполняются только в режиме `replay`.

---

## 36. Целостность верификации и интеграции

### 36.1. Проблема оракула

Раздел 25 требует `test_failures: 0`. Это условие выполняется двумя способами: сделать код корректным или согласовать тесты с текущим поведением кода. Автономный агент оптимизирует измеримую цель, поэтому второй путь является ожидаемым, а не гипотетическим.

Наблюдаемые способы подмены: переписывание ассерта, пометка теста как пропущенного или ожидаемо падающего, широкий перехват исключений, удаление падающего случая, фиксация в ожидании того значения, которое код возвращает сейчас.

Пока тестами управляет проверяемая сторона, верификация не является доказательством.

### 36.2. Разделение авторства

- тесты формируются на этапах 9.7–9.8 по спецификации, а не по реализации;
- роли Test Agent и Code Reviewer не обслуживаются той же конфигурацией модели, что Developer Agent в рамках одной задачи;
- reviewer сохраняет read-only доступ к коду.

### 36.3. Заморозка тестов

Утверждённый набор тестов задачи переводится в read-only для Developer Agent на всё время этапов 9.9–9.11 и вносится в `forbidden_paths` контракта задачи.

Изменение существующих тестов является действием класса `approval_required` наравне с `change_production`.

### 36.4. Раздельные диффы

Изменение делится на code diff и test diff. Они рассматриваются по разным политикам и представляются reviewer раздельно.

Test diff проходит проверку запрещённых конструкций:

- маркеры пропуска и ожидаемого падения;
- пустые обработчики исключений;
- отключённые или ослабленные ассерты;
- снижение порогов покрытия;
- флаги обхода проверок и hook'ов.

Совпадение блокирует завершение задачи и не может быть снято реализующим агентом.

### 36.5. Мутационная проверка

Новые тесты обязаны демонстрировать способность падать. В изменённый код вносится ограниченный набор синтетических дефектов; новые тесты должны их обнаружить.

`mutation_score` фиксируется как метрика Definition of Done. Тест, не обнаруживающий ни одного дефекта, не засчитывается как верификация.

### 36.6. Расширение Definition of Done

```yaml
definition_of_done:
  required_checks:
    - unit-tests
    - integration-tests
    - lint
    - typecheck
    - security-scan
    - specification-verification
    - test-diff-policy
    - mutation-check

  limits:
    critical_vulnerabilities: 0
    high_vulnerabilities: 0
    test_failures: 0
    forbidden_path_changes: 0
    unapproved_test_modifications: 0
    minimum_mutation_score: 0.7
```

### 36.7. Ветвление и очередь интеграции

Параллельные workstream создают ветки, которые обязаны где-то встретиться. Верификация на устаревшей базе не даёт права на merge.

- интеграция сериализуется через merge queue: rebase на текущий trunk, повторный прогон обязательных проверок на интегрированном результате, затем merge;
- одна задача — одна ветка — один change set;
- прямой push в базовую ветку, force push и переписывание истории общих веток запрещены всем агентским идентичностям;
- конфликт внутри `allowed_paths` может разрешать агент с полной повторной верификацией;
- конфликт вне `allowed_paths` или затрагивающий замороженные тесты эскалируется как человеческое решение и не расходует repair-циклы;
- коммиты атомарны и содержат в trailers идентификаторы задачи, запуска и версий промптов.

### 36.8. Учёт пропущенных дефектов

Дефект, обнаруженный после закрытия задачи, атрибутируется запуску, который его внёс, и конфигурации reviewer, которая его пропустила. `escape_defects` является метрикой качества платформы.

---

## 37. Экономика выполнения и целостность эффектов

### 37.1. Бюджетный ledger

Лимит на задачу не ограничивает суммарные расходы: сорок параллельных задач укладываются каждая в свой лимит и вместе выносят месячный бюджет. Счётчик, увеличиваемый после вызова, некорректен при параллелизме.

Расходы ведутся двухфазно:

- **резервирование** — перед шагом атомарно резервируется оценка стоимости; шаг стартует только при успешном резерве;
- **списание** — после вызова фиксируется факт, неиспользованный остаток возвращается;
- **истечение** — резерв связан с lease шага; осиротевший резерв освобождается supervisor'ом.

Бюджеты вложены: организация → проект → задача → шаг. Резерв обязан пройти на всех уровнях.

Ledger является append-only и входит в audit surface: резерв, списание и возврат атрибутируются запуску, шагу и конфигурации модели.

### 37.2. Автостоп и глобальная пауза

- скорость расхода сравнивается с прогнозом на период; превышение порога переводит платформу в режим ограниченного приёма: новые задачи не принимаются, текущие доводятся до checkpoint и паркуются;
- переход сопровождается инцидентом и снимается явным действием оператора;
- глобальная пауза — отдельный переключатель, останавливающий приём новых шагов на всей платформе с сохранением checkpoints и lease;
- аварийная остановка задачи, глобальная пауза и security read-only независимы и могут действовать одновременно.

### 37.3. Кэш модельных вызовов

- контекстные пакеты собираются prefix-stable: неизменяемые элементы первыми, волатильные последними, чтобы работал provider-side prompt caching;
- кэш точных ответов по ключу `(model_id, model_version, prompt_registry_version, request_digest, sampling)`;
- одновременные идентичные запросы схлопываются в один вызов;
- кэш отключён там, где разнообразие является целью: consensus, shadow mode, эксперименты;
- записи кэша наследуют privacy class проекта и не разделяются между проектами и privacy zones;
- попадание в кэш отображается в Run Timeline; запуск не должен выглядеть дешевле, чем он есть.

### 37.4. Ledger внешних эффектов

Идемпотентность заявлена как требование в разделах 11.3, 14.2 и 16.5, но требует механизма. Повторы гарантированы: истекают lease, падают worker'ы, брокер передаёт сообщение повторно, supervisor возвращает осиротевшие задачи.

Все эффекты, покидающие границу платформы, проходят через ledger:

```yaml
idempotency_key: sha256(run_id + step_id + effect_type + payload_digest)
effect_type: create_pull_request
target: github:ochenstarik-ui/kagent
state: intended | in_flight | succeeded | failed | unknown
external_id: null
```

Правила:

- ключ вычисляется до попытки выполнения;
- при повторе запись в состоянии `succeeded` возвращает сохранённый результат без повторного выполнения;
- запись в состоянии `unknown` блокирует шаг и порождает инцидент сверки, а не догадку;
- эффекты, порождённые изменением состояния, публикуются через outbox в одной транзакции с этим изменением;
- connector с операциями записи обязан принимать ключ идемпотентности или предоставлять естественный ключ для сверки; иначе он допускается только к чтению;
- для каждого write-connector определяется процедура сверки; её отсутствие блокирует production-использование connector'а.

---

## 38. Контракт человеческого решения

### 38.1. Принцип

Ожидание человека — нормальное состояние автономной системы, а не исключение. Оно должно быть спроектировано: кто держит ресурсы, сколько ждём, что происходит при молчании.

### 38.2. Контракт вопроса

```yaml
question_id: q-1042
run_id: run-88
task_id: task-123
kind: approval | choice | clarification | conflict
urgency: low | normal | high | blocking
statement: "Конфликт в services/auth затрагивает замороженный тест"
options:
  - id: escalate
    effect: "Передать разработчику"
  - id: abandon
    effect: "Отменить задачу, ветку сохранить"
default: null
ttl: PT12H
on_timeout: park | abort | assume_default
evidence:
  - artifact://run-88/conflict.patch
channels: [web, telegram]
```

### 38.3. Требования

- постановка вопроса освобождает worker и lease после checkpoint; ожидающая задача не потребляет вычислительную ёмкость и не держит бюджетный резерв;
- контекст возобновления хранится в checkpoint, а не в памяти процесса;
- `assume_default` допустим только при объявленном default и обратимом действии; необратимые действия используют `park` или `abort`;
- вопросы доставляются по настроенным каналам и видны в единой очереди решений по всем проектам;
- вопрос уровня `blocking` с истёкшим TTL порождает инцидент;
- ответ записывается в audit log с идентичностью ответившего и является воспроизводимым входом запуска.

---

## 39. Жизненный цикл контекста

### 39.1. Проблема

Раздел 12.5 описывает сборку пакета, но не его эволюцию на протяжении восьмидесяти ходов агента. Возникают два отказа: дрейф цели по мере вытеснения исходного задания свежим шумом и смешение инструкций с данными, полученными инструментами.

### 39.2. Требования

- каждая роль объявляет бюджет контекста в токенах; превышение вызывает компактификацию, а не молчаливое усечение;
- **якоря** никогда не суммаризируются и переутверждаются после каждой компактификации: контракт задачи, allowed и forbidden paths, Definition of Done, действующие approvals, применимая политика безопасности;
- компактификация сохраняет исходное состояние как checkpoint-артефакт, помечает сводку как сводку и указывает идентификаторы заменённого материала;
- каждый элемент контекста несёт класс происхождения: инструкция платформы, контракт задачи, память проекта, вывод инструмента, недоверенное внешнее содержимое;
- недоверенное содержимое отделяется и помечается как данные; инструкции, обнаруженные внутри данных, не выполняются, а фиксируются как событие безопасности;
- сборка и компактификация детерминированы при одинаковых входах.

---

## 40. Память и границы данных

### 40.1. Исполняемые уроки

Урок переводится в статус `active` только если он объявляет, как меняет поведение:

- **исполняемая проверка** — правило линта, политики, запрещённый шаблон, добавленный eval-случай; предпочтительная форма;
- **изменение контракта** — правка умолчаний контракта задачи, прав инструментов или политики маршрутизации;
- **правило контекста** — инъекция в контекст конкретной роли при объявленном триггере с указанием стоимости в токенах.

Дополнительно:

- урок без одной из этих форм остаётся `candidate` и не попадает ни в один контекст;
- новый урок проверяется на противоречие с действующими; противоречие разрешается через supersedes, а не сосуществование;
- урок имеет дату пересмотра; непересмотренный урок переходит в `stale` и перестаёт применяться;
- фиксируется число срабатываний и число предотвращённых дефектов, чтобы бесполезные guardrails выводились из обращения.

### 40.2. Изоляция личного контура

Личные данные отделяются конструктивно, а не классификацией на выходе:

- отдельное хранилище, отдельный поисковый индекс, отдельный bucket;
- отдельные ключи шифрования в vault: проектные credentials не расшифровывают личный материал;
- Context Builder не имеет личный контур в списке адресуемых источников для ролей разработки — независимо от конфигурации политик;
- к личному контуру обращается только Personal Assistant Agent, и он не получает инструментов записи в репозиторий;
- перенос элемента из личного контура в проект — явное аудируемое действие пользователя, а не результат поиска;
- маршрутизация по умолчанию — локальные модели; облачный поставщик требует явного согласия по категории данных;
- удаление личных данных выполняется независимо от удаления проектов и распространяется на кассеты, кэш и checkpoints.

---

## 41. Измеримость прогресса

### 41.1. Eval-suite платформы

Раздел 13.4 квалифицирует модели. Здесь измеряется сама платформа: качество промптов, сборки контекста, контрактов инструментов, политики верификации и стратегии repair.

- фиксированный набор сквозных задач на закреплённых снимках репозиториев с известным критерием приёмки;
- стратификация по категориям (feature, bugfix, refactor, dependency upgrade, security fix) и по сложности;
- каждый случай фиксирует базовый коммит, контракт задачи и критерии приёмки;
- детерминированность: без сетевых обращений вне записанных фикстур и без зависимости от календарного времени;
- регрессионные прогоны в режиме `replay`, выборочные live-прогоны в пределах объявленного бюджета.

### 41.2. Метрики автономности

- autonomy rate — доля задач, закрытых без вмешательства человека;
- число вмешательств на закрытую задачу;
- число repair-циклов на закрытую задачу;
- rework rate — доля закрытых задач, переоткрытых позднее;
- escape defects на закрытую задачу;
- стоимость успешно интегрированного изменения;
- время до первого полезного артефакта;
- число попыток нарушения политик и выхода за allowed paths.

Регресс autonomy rate или escape defects сверх объявленного допуска блокирует релиз. Изменения промптов и маршрутизации продвигаются только через этот гейт.

### 41.3. Правило честности

Eval-случаи принадлежат платформе, а не агентам. Агент, работающий над самим KAgent, не может добавлять, изменять или отключать eval-случаи в рамках продуктовой задачи. Это отдельное изменение, утверждаемое человеком.

### 41.4. Статус этапа вычисляется

Отчёт о работе, написанный исполнителем и никем не проверенный, расходится с реальностью — не из-за недобросовестности, а потому что правдоподобная сводка дешевле работающей функции.

- каждый этап и каждая возможность MVP объявляются в машиночитаемом реестре вместе с доказательством: eval-случаи, сквозной сценарий, обязательные проверки, артефакты;
- статус этапа генерируется из последнего прогона CI; возможность считается выполненной только при наличии проходящего доказательства;
- ручная правка сгенерированных блоков статуса отклоняется проверкой.

### 41.5. Обнаружение расхождения

Отдельная задача CI сравнивает заявленное с наблюдаемым и роняет сборку при:

- заявленной возможности без проходящего доказательства;
- модуле, присутствующем в дереве, но недостижимом ни из одной точки входа;
- задокументированном endpoint, отсутствующем в таблице маршрутов;
- задокументированной переменной окружения, которая нигде не читается;
- пользовательском изменении без записи в `CHANGELOG.md`;
- архитектурном изменении без ADR.

Код, недостижимый ни из одной точки входа, либо подключается, либо удаляется, и не засчитывается как поставленная возможность.

### 41.6. Честный красный

Падающая сборка основной ветки является инцидентом с назначенным владельцем. Добавление новых возможностей на красном trunk запрещено.
