# C5 — integrate NATS events

Правила работы — `AGENTS.md` в корне репозитория.
Репозиторий: `https://github.com/ochenstarik-ui/kagent`, база — свежий main.
Ветка: `wt/c5-nats-events`. Зависимостей нет; независима от c1/c4.

## Problem

`services/nats/src/events.py` недостижим и не создаёт JetStream stream. Каталог services/nats фактически библиотека.

## Work

1. Починить клиент:
- идемпотентно ensure stream перед publish/subscribe;
- единое правило stream name/subjects;
- сохранить ack/nak;
- bounded broker reconnect.

2. Перенести как shared Python library (`packages/py-events` или `services/_shared`) и обосновать по spec section 7.

3. Подключить к `services/pipeline` как реальному consumer/publisher:
- lifecycle names: task.started, agent.started, agent.completed, artifact.created, task.failed;
- required ADR-0002 envelope: id, type, schema version, time, project/task IDs, correlation ID;
- NATS_URL with default and .env.example;
- nats-py version same as orchestrator; document necessity/provenance/license;
- docker-compose pipeline depends_on healthy nats;
- broker failure is logged best-effort and must not fail pipeline; explicitly document no outbox yet.

4. Tests:
- unit broker stub: serialization required fields, same stream rule publish/subscribe, broker unavailable does not interrupt;
- CI integration with `nats:2.11-alpine` + JetStream, publish/receive and repeated ensure stream;
- capability evidence references new job;
- remove NATS entry from known-drift.

## Acceptance

- `ruff check services scripts`
- `python -m pytest tests/unit -q`
- `python scripts/drift_check.py`
- product import from real service; NATS path absent from drift; known-drift 2 or 1 if C3 merged;
- broker CI job green;
- roadmap_status before/after shows event-stream capability verified by evidence;
- green CI URL.

## Do not

No Control Plane event client, no outbox, no orchestrator integration. No force push. Do not merge.
