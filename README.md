# KAgent

KAgent — самостоятельная self-hosted мультиагентная платформа для автономной разработки программного обеспечения и работы персонального помощника.

## Статус

Текущая версия: **0.9.0-dev — Agent Workspace Cockpit Foundation**.

Текущая линия разработки включает foundation-компоненты и Agent Workspace Cockpit:

- monorepo;
- versioned contracts;
- capability-first Reasoning Engine architecture;
- budget-aware multi-model routing policy;
- Web-клиент;
- TypeScript Control Plane;
- Rust Gateway;
- локальную инфраструктуру PostgreSQL, NATS JetStream и MinIO;
- ADR, threat model и журналы изменений.

## Быстрый старт

Требования:

- Node.js 22+
- pnpm 10+
- Rust stable
- Docker Compose

```bash
cp .env.example .env
docker compose up -d
pnpm install
pnpm check
```

Запуск Web:

```bash
pnpm --filter @kagent/web dev
```

Запуск Control Plane:

```bash
pnpm --filter @kagent/control-plane dev
```

Запуск Gateway:

```bash
cargo run --manifest-path services/gateway/Cargo.toml
```

## Основные документы

- [Полное ТЗ](docs/KAGENT_FULL_PRODUCT_SPEC.md)
- [Архитектура](docs/ARCHITECTURE.md)
- [Threat model](docs/THREAT_MODEL.md)
- [Roadmap](docs/ROADMAP.md)
- [ADR](docs/adr/README.md)
- [Журнал изменений](CHANGELOG.md)
- [Журнал агентов](AGENT_CHANGELOG.md)

## Лицензия

Лицензия пока не выбрана. До добавления `LICENSE` проект не предоставляется для свободного переиспользования.

## Agent Workspace Cockpit 0.9

Release 0.9 adds governed workspace contracts, lifecycle APIs, session metadata,
line-level diff review, PostgreSQL migration 003 and the `/workspaces` Web UI.
See [Agent Workspace Cockpit](docs/AGENT_WORKSPACE_COCKPIT.md) for verified scope
and explicit limitations. Physical Git worktrees, PTY/Chromium processes and CLI
agent harnesses remain planned for 0.10+.