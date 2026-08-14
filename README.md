# KAgent

KAgent — самостоятельная self-hosted мультиагентная платформа для автономной разработки программного обеспечения и работы персонального помощника.

## Статус

Текущая версия: **0.2.0-rc.1 — Server Release Candidate**.

Релиз-кандидат включает рабочий вертикальный срез платформы:

- monorepo;
- versioned contracts;
- capability-first Reasoning Engine architecture;
- budget-aware multi-model routing policy;
- Web-клиент;
- TypeScript Control Plane;
- Rust Gateway;
- локальную инфраструктуру PostgreSQL, NATS JetStream и MinIO;
- sandboxed Agent Runtime, проверяемый coding pipeline и multi-agent orchestration;
- авторизацию, RBAC, TOTP, аудит и observability;
- Web dashboard и сквозной Playwright E2E;
- production Compose с HTTPS, миграциями и резервным копированием;
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

Развёртывание на сервере выполняется только по
[production runbook](docs/DEPLOYMENT.md) через `./scripts/deploy_server.sh`.

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
