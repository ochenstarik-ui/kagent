# KAgent

KAgent — самостоятельная self-hosted мультиагентная платформа для автономной разработки программного обеспечения и работы персонального помощника.

## Статус

Текущая версия: **0.10.0-dev — Workspace Provisioner Foundation**.

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

## Workspace Provisioner 0.10

Release 0.10 persists projects, tasks and workspaces in PostgreSQL, issues
immutable task contracts, manages restart-safe worker leases and provisions
idempotent worker-owned Git worktrees behind opaque references. The existing
/workspaces cockpit remains the operational UI.

See [Agent Workspace Cockpit](docs/AGENT_WORKSPACE_COCKPIT.md) for verified scope
and limitations. PTY, browser and agent-harness streaming remain planned for
0.11+. Production hardening in the threat model is still required.