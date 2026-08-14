#!/usr/bin/env bash
set -euo pipefail

compose=(docker compose)
db="${POSTGRES_DB:-kagent}"
user="${POSTGRES_USER:-kagent}"

"${compose[@]}" up -d postgres
for _ in $(seq 1 60); do
  if "${compose[@]}" exec -T postgres pg_isready -U "$user" -d "$db" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
"${compose[@]}" exec -T postgres pg_isready -U "$user" -d "$db" >/dev/null

psql_cmd=("${compose[@]}" exec -T postgres psql -v ON_ERROR_STOP=1 -U "$user" -d "$db")
"${psql_cmd[@]}" -f /docker-entrypoint-initdb.d/000_schema_migrations.sql

# Baseline installations created before the migration ledger was introduced.
declare -A markers=(
  [001_initial_schema.sql]="to_regclass('public.projects') IS NOT NULL"
  [002_auth.sql]="to_regclass('public.accounts') IS NOT NULL"
  [003_audit_immutability.sql]="EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'audit_events_no_update')"
  [004_totp_persistence.sql]="to_regclass('public.totp_challenges') IS NOT NULL"
  [005_recovery_codes.sql]="to_regclass('public.recovery_codes') IS NOT NULL"
)

for filename in 001_initial_schema.sql 002_auth.sql 003_audit_immutability.sql 004_totp_persistence.sql 005_recovery_codes.sql; do
  applied=$("${psql_cmd[@]}" -Atc "SELECT EXISTS (SELECT 1 FROM schema_migrations WHERE filename = '$filename')")
  if [[ "$applied" != "t" ]]; then
    present=$("${psql_cmd[@]}" -Atc "SELECT ${markers[$filename]}")
    if [[ "$present" == "t" ]]; then
      "${psql_cmd[@]}" -c "INSERT INTO schema_migrations(filename) VALUES ('$filename') ON CONFLICT DO NOTHING"
    fi
  fi
done

for migration in $(find migrations -maxdepth 1 -type f -name '*.sql' -printf '%f\n' | sort); do
  applied=$("${psql_cmd[@]}" -Atc "SELECT EXISTS (SELECT 1 FROM schema_migrations WHERE filename = '$migration')")
  if [[ "$applied" == "t" ]]; then
    printf 'already applied: %s\n' "$migration"
    continue
  fi
  printf 'applying: %s\n' "$migration"
  "${psql_cmd[@]}" -f "/docker-entrypoint-initdb.d/$migration"
  "${psql_cmd[@]}" -c "INSERT INTO schema_migrations(filename) VALUES ('$migration') ON CONFLICT DO NOTHING"
done

echo "Database migrations are current."
