# Roadmap

> Статусы этапов 0.1–0.8 проставлены вручную и не подтверждены доказательствами выполнения.
> До внедрения вычисляемого статуса (ADR-0016, ТЗ 41.4) считать их заявленными, а не подтверждёнными.

## 0.1 — Foundation Bootstrap ✅
## 0.2 — Persistent Project and Task Lifecycle ✅
## 0.3 — Authentication and Policy Foundation ✅
## 0.4 — Single-Agent Runtime ✅
## 0.5 — Verified Coding Pipeline ✅
## 0.6 — Observability ✅
## 0.7 — Docker Compose ✅
## 0.8 — Complete ✅

- [x] Web UI (Next.js dashboard)
- [x] NATS event streaming
- [x] Multi-agent orchestration
- [x] Production deployment guide
- [x] Integration tests with real PostgreSQL

## 0.9 — Trust and Economics Foundation

Реализация ADR-0004…ADR-0016. Порядок отражает зависимости: сначала зелёная сборка
и вычисляемый статус, затем воспроизводимость, затем целостность верификации,
затем экономика.

### 0.9.0 — Green trunk (предусловие)

- [ ] pnpm-lock.yaml в репозитории, node-job проходит
- [ ] gateway компилируется, `cargo fmt --check` и `clippy -D warnings` проходят
- [ ] control-plane стартует и работает на PostgreSQL, а не на in-memory store
- [ ] Python-job в CI: линт и тесты для сервисов

### 0.9.1 — Измеримость (ADR-0008, ADR-0016)

- [ ] Машиночитаемый реестр возможностей и доказательств
- [ ] Вычисляемый статус этапов из артефактов CI
- [ ] Spec drift check: недостижимый код, недокументированные маршруты, отсутствующие changelog и ADR
- [ ] Eval-suite платформы и метрики автономности

### 0.9.2 — Воспроизводимость (ADR-0004, ADR-0007, ADR-0012)

- [ ] Кассеты модельных вызовов и режимы live/record/replay
- [ ] Реестр промптов с версионированием
- [ ] Детерминированная сборка контекста, якоря и политика компактификации

### 0.9.3 — Целостность верификации (ADR-0005, ADR-0009)

- [ ] Разделение code diff и test diff, заморозка тестов
- [ ] Проверка запрещённых конструкций в test diff
- [ ] Мутационная проверка новых тестов
- [ ] Merge queue, защита trunk, политика конфликтов

### 0.9.4 — Экономика и эффекты (ADR-0006, ADR-0010, ADR-0013)

- [ ] Двухфазный бюджетный ledger, иерархия бюджетов
- [ ] Автостоп по burn rate и глобальная пауза
- [ ] Ledger внешних эффектов, outbox, процедуры сверки
- [ ] Кэш модельных вызовов и prefix-stable контекст

### 0.9.5 — Взаимодействие и границы (ADR-0011, ADR-0014, ADR-0015)

- [ ] Контракт человеческого решения с TTL и единой очередью
- [ ] Исполняемые уроки и вывод бесполезных guardrails из обращения
- [ ] Изоляция личного контура

## 1.0 — Future

- [ ] Agent sandbox hardening (gVisor/Firecracker)
- [ ] Multi-tenancy isolation
- [ ] Horizontal scaling (K8s)
- [ ] gRPC streaming for agent events
- [ ] Plugin system for custom tools
- [ ] Android client
