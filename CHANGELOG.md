# Changelog

Все заметные изменения KAgent фиксируются в этом файле.

Формат основан на Keep a Changelog. Проект следует Semantic Versioning после первого стабильного релиза.

## [Unreleased]

### Added

- Архитектурное решение Capability-first Reasoning Engine с бюджетным Router, режимами Economy/Balanced/Critical и оценкой по стоимости успешной задачи.

- Чистая monorepo-структура KAgent.
- Базовый Web-клиент.
- Каркас TypeScript Control Plane.
- Каркас Rust Gateway.
- Пакет versioned-контрактов.
- Docker Compose с PostgreSQL, NATS JetStream и MinIO.
- Архитектурные документы, ADR и threat model.
- Начальный тестовый и CI-каркас.

### Changed

- Полное ТЗ приведено к разработке с чистого листа без этапа миграции legacy-кода.

## [0.9.0-dev] - 2026-08-03

### Added

- Governed AgentWorkspace, WorkspaceSession and DiffReviewComment contracts.
- Workspace lifecycle API with mandatory verification before completion.
- Session concurrency, network-default-deny and review path guards.
- Agent Workspace Cockpit at `/workspaces`.
- PostgreSQL migration `003_agent_workspaces.sql`.
- ADR-0004 and a verified implementation-status document.

### Changed

- Aligned root, contracts, Web and Control Plane versions on `0.9.0-dev`.
- Added missing Node/PostgreSQL type dependencies required by strict builds.
- Fixed malformed password-record handling and exact optional property builds.
- Documented 0.10-1.0 roadmap without claiming unimplemented processes.

### Security

- Public workspace state uses opaque references instead of host paths.
- Repository credentials are stripped before workspace state is returned.
- Network is denied by default and agent concurrency is bounded.
- Workspace completion requires the verification state.