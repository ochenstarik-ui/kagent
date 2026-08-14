# KAgent single-server deployment

This runbook deploys KAgent behind Caddy with automatic TLS. The base Compose
file is suitable for local development; a server must also use
`compose.production.yml`.

## Server prerequisites

- Ubuntu 24.04 LTS or another current Linux distribution
- Docker Engine 24+ and Docker Compose v2
- 8 GB RAM recommended, 4 GB minimum
- at least 40 GB free disk plus capacity for workspaces and backups
- kernel user namespaces and `bwrap` support
- a DNS `A`/`AAAA` record pointing the KAgent hostname to the server
- inbound firewall ports `22`, `80`, and `443` only

Do not publish PostgreSQL, NATS, MinIO, or Gateway port 8080. The base Compose
file binds their diagnostic ports to loopback; Caddy is the only public entry.

## First installation

Deploy a reviewed tag or an explicitly recorded commit, not a moving branch:

```bash
git clone https://github.com/ochenstarik-ui/kagent.git
cd kagent
git checkout <release-tag-or-commit>
cp .env.example .env
chmod 600 .env
```

Generate unique values and edit `.env`:

```bash
openssl rand -hex 24  # POSTGRES_PASSWORD
openssl rand -hex 32  # JWT_SECRET
openssl rand -hex 32  # KAGENT_SERVICE_SECRET
openssl rand -hex 24  # S3_SECRET_KEY
```

Set `KAGENT_DOMAIN` to the real hostname and configure at least one provider
key. If OpenCode-Go runs on the Docker host, keep
`OPENCODE_GO_ENDPOINT=http://host.docker.internal:20127`; `localhost` would
refer to the reasoning-engine container itself.

Run the guarded deployment:

```bash
./scripts/deploy_server.sh
```

The script rejects placeholders, short secrets, public Gateway binding,
world-readable `.env`, a missing model provider, invalid Compose, failed
migrations, and an unhealthy HTTPS endpoint.

## Verification

```bash
curl --fail https://$KAGENT_DOMAIN/health/live
curl --fail https://$KAGENT_DOMAIN/api/control-plane/health/live
curl --fail https://$KAGENT_DOMAIN/api/reasoning/health/live
curl --fail https://$KAGENT_DOMAIN/api/observability/v1/health
docker compose -f docker-compose.yml -f compose.production.yml ps
```

Before admitting real work, run one controlled task through the configured
provider, reasoning engine, sandboxed runtime, verification pipeline, and Git
result. The replay suite and deployment smoke test do not prove external
provider credentials or repository permissions.

## Updates and migrations

Create a backup before every update:

```bash
./scripts/backup.sh
git fetch --tags origin
git checkout <new-release-tag>
./scripts/deploy_server.sh
```

`scripts/migrate.sh` maintains `schema_migrations`, baselines installations
created before the ledger, and applies only pending SQL files in lexical order.
Docker's `/docker-entrypoint-initdb.d` mechanism runs only on the first startup
of an empty PostgreSQL volume and does not apply newly added migration files to
an existing database; never use it as the upgrade procedure.

## Backup and restore

`scripts/backup.sh` creates:

- a PostgreSQL custom-format logical dump;
- a consistent maintenance snapshot of NATS JetStream, MinIO, agent
  workspaces, and Caddy state;
- a manifest containing the Git commit and timestamp.

Stateful writers are paused briefly during the volume snapshot. Copy the
resulting `backups/<timestamp>` directory to separate encrypted storage.

Restore is intentionally fail-closed and destructive:

```bash
KAGENT_RESTORE_CONFIRM=ERASE_AND_RESTORE \
  ./scripts/restore.sh backups/<timestamp>
```

Test restoration on a separate server before relying on backups in production.

## Operations

All services use `restart: unless-stopped` and bounded `json-file` logs.

```bash
docker compose -f docker-compose.yml -f compose.production.yml ps
docker compose -f docker-compose.yml -f compose.production.yml logs --tail=200
docker stats
```

Prometheus-compatible metrics are available at
`https://$KAGENT_DOMAIN/api/observability/v1/metrics`. Alert at minimum on
endpoint failure, repeated container restarts, disk usage, failed backups,
PostgreSQL availability, provider throttling, and a growing task failure rate.

## Security checklist

- keep `.env` mode `0600` and never commit it;
- allow SSH keys only and disable password/root SSH login;
- enable automatic OS security updates;
- keep Docker and pinned service images patched through reviewed releases;
- rotate provider keys and service secrets after suspected exposure;
- review the append-only audit log and `docs/THREAT_MODEL.md`;
- store backups off-server and encrypt them;
- do not expose ports 5432, 4222, 8222, 9000, 9001, or 8080 publicly.

## Rollback

Application rollback is a Git checkout of the previous recorded tag followed
by `./scripts/deploy_server.sh`. Database migrations are forward-only; if a
release requires schema rollback, restore the pre-update backup instead of
manually editing production tables.
