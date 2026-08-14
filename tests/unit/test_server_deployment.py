import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_base_compose_is_restartable_and_not_public_by_default() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "restart: unless-stopped" in compose
    assert '"${GATEWAY_BIND_ADDRESS:-127.0.0.1}' in compose
    assert "minio/minio:latest" not in compose
    assert "minio/minio:RELEASE." in compose
    for service in (
        "postgres",
        "nats",
        "minio",
        "gateway",
        "control-plane",
        "reasoning-engine",
        "agent-runtime",
        "pipeline",
        "observability",
        "web",
    ):
        block = re.search(
            rf"^  {re.escape(service)}:\n(?P<body>.*?)(?=^  [a-z][a-z0-9-]*:\n|^volumes:)",
            compose,
            re.MULTILINE | re.DOTALL,
        )
        assert block is not None
        assert "<<: *service-defaults" in block.group("body")


def test_production_overlay_requires_secrets_and_terminates_tls() -> None:
    compose = (ROOT / "compose.production.yml").read_text(encoding="utf-8")
    for variable in (
        "POSTGRES_PASSWORD",
        "JWT_SECRET",
        "KAGENT_SERVICE_SECRET",
        "S3_ACCESS_KEY",
        "S3_SECRET_KEY",
        "KAGENT_DOMAIN",
    ):
        assert f"${{{variable}:?" in compose
    assert "caddy:2.10.2-alpine" in compose
    assert '"80:80"' in compose
    assert '"443:443"' in compose


def test_every_initdb_migration_records_its_filename() -> None:
    for migration in sorted((ROOT / "migrations").glob("*.sql")):
        sql = migration.read_text(encoding="utf-8")
        assert "schema_migrations" in sql
        assert migration.name in sql


def test_restore_requires_explicit_destructive_confirmation() -> None:
    restore = (ROOT / "scripts" / "restore.sh").read_text(encoding="utf-8")
    assert 'KAGENT_RESTORE_CONFIRM:-}" != "ERASE_AND_RESTORE"' in restore
    assert "dropdb" in restore
