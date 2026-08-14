# ADR 0033: Single-server production deployment

## Status

Accepted

## Context

The development Compose stack started successfully but lacked automatic
restart, bounded logs, TLS, guarded secrets, repeatable upgrades, and a complete
state backup. Deploying that file directly on an Internet-facing server would
create avoidable availability and security failures.

## Decision

The first operational topology is one Linux host running Docker Compose.
`docker-compose.yml` remains the common service definition and binds the
Gateway to loopback. `compose.production.yml` adds Caddy as the only public
entry point on ports 80/443 and makes production secrets mandatory.

All long-running services use `restart: unless-stopped`, Docker's init process,
bounded JSON logs, health checks, and named persistent volumes. SQL upgrades
are recorded in `schema_migrations`; backup and explicit-confirmation restore
scripts cover PostgreSQL, NATS, MinIO, agent workspaces, and Caddy state.

Deployments must use a reviewed tag or pinned commit and pass the production
preflight before Compose is changed.

## Consequences

- a single server is straightforward to operate and recover;
- the topology is not highly available and maintenance can cause downtime;
- horizontal scaling requires external PostgreSQL/object storage, clustered
  NATS, and a durable account-leasing implementation;
- TLS certificate issuance requires working public DNS and ports 80/443.
