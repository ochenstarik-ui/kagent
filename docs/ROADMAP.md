# Roadmap

## 0.1 — Foundation Bootstrap ✅
- [x] Clean monorepo
- [x] Core contracts
- [x] Web skeleton
- [x] Control Plane skeleton
- [x] Gateway skeleton
- [x] Local infrastructure
- [x] ADR and threat model
- [x] CI skeleton

## 0.2 — Persistent Project and Task Lifecycle ✅
- [x] PostgreSQL migrations (001_initial_schema)
- [x] Project CRUD
- [x] Task creation and state transitions
- [x] Append-only audit events
- [x] Control Plane Fastify API

## 0.3 — Authentication and Policy Foundation ✅
- [x] Account registration/login
- [x] Password hashing (PBKDF2 100K SHA-512)
- [x] JWT access + refresh tokens with rotation
- [x] Sessions and revocation
- [x] RBAC and project membership

## 0.4 — Single-Agent Runtime ✅
- [x] Tool contracts (file_read, file_write, shell)
- [x] Permission system
- [x] Isolated workspace per task
- [x] Streaming execution events
- [x] Artifact management

## 0.5 — Verified Coding Pipeline ✅
- [x] Planner (feature/bugfix/refactor templates)
- [x] Tester (test suite execution)
- [x] Independent reviewer (criteria check)
- [x] Repair loop (max 3 cycles)
- [x] Definition of Done gate

## 0.6 — Observability ✅
- [x] Prometheus-compatible metrics
- [x] Service health aggregation
- [x] Alert system
- [x] Human-readable dashboard

## 0.7 — Docker Compose ✅
- [x] Full service orchestration (8 services)
- [x] .env.example
- [x] Healthchecks for all services
- [x] Dockerfiles for all services

## 0.8 — Next
- [ ] Web UI (Next.js dashboard)
- [ ] NATS event streaming
- [ ] Multi-agent orchestration
- [ ] Production deployment guide
- [ ] Integration tests with real PostgreSQL
