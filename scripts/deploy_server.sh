#!/usr/bin/env bash
set -euo pipefail

python3 scripts/server_preflight.py --env .env
docker compose -f docker-compose.yml -f compose.production.yml config -q
./scripts/migrate.sh
docker compose -f docker-compose.yml -f compose.production.yml up -d --build --remove-orphans

domain="$(sed -n 's/^KAGENT_DOMAIN=//p' .env | tail -n 1)"
for _ in $(seq 1 90); do
  if curl --fail --silent --show-error "https://$domain/health/live" >/dev/null; then
    echo "KAgent is healthy at https://$domain"
    exit 0
  fi
  sleep 2
done

docker compose -f docker-compose.yml -f compose.production.yml ps
docker compose -f docker-compose.yml -f compose.production.yml logs --tail=200 gateway caddy
echo "Deployment did not become healthy." >&2
exit 1
