#!/usr/bin/env bash
set -euo pipefail

compose=(docker compose -f docker-compose.yml -f compose.production.yml)
backup_root="${BACKUP_DIR:-./backups}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
destination="$backup_root/$timestamp"
mkdir -p "$destination"
chmod 700 "$backup_root" "$destination"

echo "Creating PostgreSQL logical backup..."
"${compose[@]}" exec -T postgres pg_dump \
  -U "${POSTGRES_USER:-kagent}" \
  -d "${POSTGRES_DB:-kagent}" \
  --format=custom > "$destination/postgres.dump"

echo "Pausing stateful writers for a consistent volume snapshot..."
"${compose[@]}" stop pipeline agent-runtime reasoning-engine nats minio
resume_services() {
  "${compose[@]}" up -d nats minio reasoning-engine agent-runtime pipeline >/dev/null
}
trap resume_services EXIT

"${compose[@]}" --profile maintenance run --rm backup-helper sh -euc \
  "tar -czf /backups/$timestamp/state-volumes.tar.gz -C /volumes nats minio workspaces caddy-data caddy-config"

cat > "$destination/manifest.txt" <<EOF
created_at=$timestamp
git_commit=$(git rev-parse HEAD)
postgres_db=${POSTGRES_DB:-kagent}
postgres_user=${POSTGRES_USER:-kagent}
EOF
chmod 600 "$destination"/*
trap - EXIT
resume_services
echo "Backup complete: $destination"
