# E8 — Deployment smoke delivery report

## Статус

E8 принят, независимо проверен и squash-merged через PR #31.

- PR: https://github.com/ochenstarik-ui/kagent/pull/31
- Merge commit: `0940d3067d30ed028f26af2577b00a55792ec5b4`
- Exact green PR run: https://github.com/ochenstarik-ui/kagent/actions/runs/31687759474
- Green post-merge main run: https://github.com/ochenstarik-ui/kagent/actions/runs/31688669359
- Intentional-red perimeter run: https://github.com/ochenstarik-ui/kagent/actions/runs/31688253112

## Изменения

Pinned range `d3931b56ddae5e16093874e2e1555247534ea92f..0940d3067d30ed028f26af2577b00a55792ec5b4`:

- `.github/workflows/ci.yml`
- `AGENT_CHANGELOG.md`
- `CHANGELOG.md`
- `docs/DEPLOYMENT.md`
- `docs/ROADMAP.md`
- `docs/capabilities.json`
- `scripts/deployment_smoke.py`
- `tests/unit/test_deployment_smoke.py`

Итого: 8 файлов, 611 добавлений, 7 удалений.

## Доказанное поведение

- Полный Docker Compose stack собирается и достигает readiness по healthchecks.
- Все внешние действия smoke выполняются через опубликованный Gateway.
- Register → login → project create → task create → task read → audit read проходят.
- Observability вызывается через Gateway; фактический aggregate и service states записываются без ложного green.
- Runtime без service secret возвращает HTTP 401.
- Порты control-plane, reasoning-engine, agent-runtime, pipeline и observability закрыты с хоста.
- На непустом PostgreSQL volume новый файл `docker-entrypoint-initdb.d` не применяется.
- Compose logs и ps сохраняются как обязательные artifacts.

## Intentional-red доказательство

Disposable mutation опубликовала `control-plane:8100`. Два независимых oracle корректно сделали run красным:

1. `test_compose_does_not_publish_internal_service_ports`;
2. runtime validator: `internal service control-plane publishes a host port`.

Disposable remote/local branch удалена; mutation не попала в PR или `main`.

## Отдельные product findings

1. Observability aggregate остаётся `degraded`: сервис использует container-local `localhost` для проверок других контейнеров. E8 честно записывает finding; product logic/config не менялись в smoke-задаче.
2. При обязательной terminal migration probe остановка PostgreSQL вызывает в Control Plane необработанную pool error `57P01`; Control Plane завершается. Основной Gateway scenario и readiness доказаны до destructive probe. Исправление product lifecycle не входило в E8.
3. `docker-entrypoint-initdb.d` не является механизмом обновления существующей схемы; это отражено в deployment documentation.

## Безопасность delivery

`compose.redacted.log` содержит только очищенную копию. Password-like значения заменены на `[REDACTED]`; raw secrets и connection strings в пакет не включены.
