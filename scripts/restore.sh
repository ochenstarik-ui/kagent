#!/usr/bin/env bash
set -euo pipefail

if [[ "${KAGENT_RESTORE_CONFIRM:-}" != "ERASE_AND_RESTORE" ]]; then
  echo "Refusing destructive restore. Set KAGENT_RESTORE_CONFIRM=ERASE_AND_RESTORE." >&2
  exit 2
fi
if [[ $# -ne 1 ]]; then
  echo "Usage: KAGENT_RESTORE_CONFIRM=ERASE_AND_RESTORE $0 backups/TIMESTAMP" >&2
  exit 2
fi

source_dir="$(cd "$1" && pwd)"
[[ -s "$source_dir/postgres.dump" ]] || { echo "Missing postgres.dump" >&2; exit 1; }
[[ -s "$source_dir/state-volumes.tar.gz" ]] || { echo "Missing state-volumes.tar.gz" >&2; exit 1; }

compose=(docker compose -f docker-compose.yml -f compose.production.yml)
db="${POSTGRES_DB:-kagent}"
user="${POSTGRES_USER:-kagent}"

"${compose[@]}" stop caddy gateway web control-plane pipeline agent-runtime reasoning-engine observability nats minio
"${compose[@]}" up -d postgres
for _ in $(seq 1 60); do
  "${compose[@]}" exec -T postgres pg_isready -U "$user" >/dev/null 2>&1 && break
  sleep 2
done

"${compose[@]}" exec -T postgres dropdb -U "$user" --if-exists "$db"
"${compose[@]}" exec -T postgres createdb -U "$user" "$db"
"${compose[@]}" exec -T postgres pg_restore -U "$user" -d "$db" --clean --if-exists < "$source_dir/postgres.dump"

restore_name="$(basename "$source_dir")"
restore_parent="$(dirname "$source_dir")"
BACKUP_DIR="$restore_parent" "${compose[@]}" --profile maintenance run --rm backup-helper sh -euc \
  "find /volumes/nats /volumes/minio /volumes/workspaces /volumes/caddy-data /volumes/caddy-config -mindepth 1 -delete; tar -xzf /backups/$restore_name/state-volumes.tar.gz -C /volumes"

"${compose[@]}" up -d
echo "Restore complete. Verify health and application data before reopening traffic."
