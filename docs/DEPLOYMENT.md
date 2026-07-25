# KAgent Production Deployment Guide

## 1. Prerequisites

- Docker Engine 24+ with Compose v2
- 4 GB RAM minimum (8 GB recommended)
- 20 GB disk space
- Linux server (Ubuntu 22.04+ recommended) or macOS

## 2. Quick Start

```bash
git clone https://github.com/ochenstarik-ui/kagent.git
cd kagent
cp .env.example .env
# EDIT .env: change all passwords and JWT_SECRET!
docker compose up -d
```

Verify:

```bash
curl http://localhost:8080/health/live        # Gateway
curl http://localhost:8100/health/live        # Control Plane
curl http://localhost:8200/health/live        # Reasoning Engine
curl http://localhost:8500/v1/health          # Dashboard aggregator
```

## 3. Environment Variables

| Variable | Default | Required |
|----------|---------|----------|
| `POSTGRES_PASSWORD` | `change-me-locally` | **CHANGE** |
| `JWT_SECRET` | `dev-secret-...` | **CHANGE** (min 32 chars) |
| `S3_SECRET_KEY` | `change-me-locally` | **CHANGE** |
| `OPENCODE_GO_API_KEY` | — | Optional |
| `XAI_API_KEY` | — | Optional |
| `OPENAI_API_KEY` | — | Optional |

## 4. Service Architecture

```
                    ┌─────────────┐
                    │   Gateway   │ :8080 (public)
                    │   Rust      │
                    └──┬───┬───┬──┘
                       │   │   │
         ┌─────────────┘   │   └──────────────┐
         ▼                 ▼                  ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│Control Plane│  │  Reasoning  │  │Observability│
│   :8100     │  │  :8200      │  │   :8500     │
│ TypeScript  │  │  Python     │  │  Python     │
└──────┬──────┘  └─────────────┘  └─────────────┘
       │
       ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ PostgreSQL  │     │Agent Runtime│     │  Pipeline   │
│   :5432     │     │   :8300     │◄────│   :8400     │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │
       ▼                   ▼
┌─────────────┐     ┌─────────────┐
│    NATS     │     │  Workspace  │
│   :4222     │     │  Volumes    │
└─────────────┘     └─────────────┘
```

## 5. Database Migrations

Migrations are applied automatically on first startup via `docker-entrypoint-initdb.d/`.
For manual migration:

```bash
docker compose exec postgres psql -U kagent -d kagent -f /docker-entrypoint-initdb.d/001_initial_schema.sql
docker compose exec postgres psql -U kagent -d kagent -f /docker-entrypoint-initdb.d/002_auth.sql
```

## 6. Backup & Restore

### Backup

```bash
docker compose exec postgres pg_dump -U kagent kagent > kagent-backup-$(date +%Y%m%d).sql
docker compose cp minio:/data ./minio-backup/
```

### Restore

```bash
docker compose up -d postgres
docker compose exec -T postgres psql -U kagent kagent < kagent-backup.sql
docker compose up -d
```

## 7. Monitoring

- Prometheus metrics: `GET /v1/metrics` on Observability (:8500)
- Health dashboard: `GET /v1/health` on Observability (:8500)
- Service health: each service has `/health/live`

Prometheus scrape config:

```yaml
scrape_configs:
  - job_name: kagent
    static_configs:
      - targets: ['localhost:8500']
    metrics_path: /v1/metrics
```

## 8. Security Checklist

- [ ] Change all default passwords in .env
- [ ] Set JWT_SECRET to 64+ random characters: `openssl rand -hex 32`
- [ ] Configure firewall: only expose Gateway port 8080
- [ ] Enable TLS with reverse proxy (nginx/caddy)
- [ ] Set up regular database backups
- [ ] Review threat model: `docs/THREAT_MODEL.md`
- [ ] Rotate API keys quarterly
- [ ] Monitor audit log for suspicious activity

## 9. Scaling

For production workloads:

- **PostgreSQL**: Connection pool max_connections=100, add read replicas
- **Control Plane**: Scale horizontally behind load balancer
- **Agent Runtime**: One instance per concurrent agent, isolated workspaces
- **NATS**: Cluster mode for high availability
- **Gateway**: Can be scaled horizontally (stateless)

## 10. Troubleshooting

| Symptom | Check |
|---------|-------|
| Gateway 502 | `docker compose logs control-plane` |
| Auth errors | JWT_SECRET matches, sessions not expired |
| DB connection | `docker compose exec postgres pg_isready` |
| Agent stuck | `docker compose logs agent-runtime` |
| Pipeline fails | Check max_repair_cycles, review event log |
