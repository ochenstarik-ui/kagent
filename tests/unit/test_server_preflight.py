from pathlib import Path

from scripts.server_preflight import parse_env, validate


def valid_values() -> dict[str, str]:
    return {
        "POSTGRES_PASSWORD": "p" * 24,
        "JWT_SECRET": "j" * 64,
        "KAGENT_SERVICE_SECRET": "s" * 64,
        "S3_ACCESS_KEY": "kagent-prod",
        "S3_SECRET_KEY": "m" * 32,
        "KAGENT_DOMAIN": "agents.example.net",
        "GATEWAY_BIND_ADDRESS": "127.0.0.1",
        "OPENAI_API_KEY": "configured",
    }


def test_parse_env_ignores_comments_and_unquotes(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("# comment\nA='one'\nB=two\n", encoding="utf-8")
    assert parse_env(env) == {"A": "one", "B": "two"}


def test_valid_production_environment_passes(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("", encoding="utf-8")
    env.chmod(0o600)
    assert validate(valid_values(), env) == []


def test_placeholders_public_gateway_and_missing_provider_fail(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("", encoding="utf-8")
    env.chmod(0o600)
    values = valid_values()
    values.update(
        {
            "JWT_SECRET": "change-me-production-min-32-chars",
            "KAGENT_DOMAIN": "kagent.example.com",
            "GATEWAY_BIND_ADDRESS": "0.0.0.0",
            "OPENAI_API_KEY": "",
        }
    )
    errors = validate(values, env)
    assert any("placeholder" in error for error in errors)
    assert any("real server hostname" in error for error in errors)
    assert any("loopback" in error for error in errors)
    assert any("model provider" in error for error in errors)


def test_numbered_pool_key_counts_as_provider_configuration(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("", encoding="utf-8")
    env.chmod(0o600)
    values = valid_values()
    values["OPENAI_API_KEY"] = ""
    values["OPENAI_1_API_KEY"] = "configured"
    assert validate(values, env) == []
