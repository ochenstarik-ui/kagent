#!/usr/bin/env python3
"""Fail closed when a production server configuration is unsafe."""

from __future__ import annotations

import argparse
import os
import re
import stat
from pathlib import Path


PLACEHOLDERS = ("change-me", "example.com", "not-for-production")
LOOPBACK_BINDS = {"127.0.0.1", "::1", "localhost"}


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def validate(values: dict[str, str], env_path: Path) -> list[str]:
    errors: list[str] = []
    minimum_lengths = {
        "POSTGRES_PASSWORD": 16,
        "JWT_SECRET": 32,
        "KAGENT_SERVICE_SECRET": 32,
        "S3_ACCESS_KEY": 8,
        "S3_SECRET_KEY": 16,
    }
    for key, minimum in minimum_lengths.items():
        value = values.get(key, "")
        if len(value) < minimum:
            errors.append(f"{key} must contain at least {minimum} characters")
        if any(marker in value.lower() for marker in PLACEHOLDERS):
            errors.append(f"{key} still contains a placeholder")

    domain = values.get("KAGENT_DOMAIN", "")
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", domain):
        errors.append("KAGENT_DOMAIN must be a hostname without a scheme or path")
    if domain.endswith("example.com") or domain in {"localhost", "127.0.0.1"}:
        errors.append("KAGENT_DOMAIN must be the real server hostname")

    bind = values.get("GATEWAY_BIND_ADDRESS", "127.0.0.1")
    if bind not in LOOPBACK_BINDS:
        errors.append("GATEWAY_BIND_ADDRESS must stay on loopback behind Caddy")

    provider_keys = [
        value
        for key, value in values.items()
        if key in {"OPENCODE_GO_API_KEY", "XAI_API_KEY", "OPENAI_API_KEY"}
        or re.fullmatch(r"(?:OPENCODE_GO|XAI|OPENAI)_\d+_API_KEY", key)
    ]
    if not any(provider_keys):
        errors.append("configure at least one model provider API key")

    if os.name == "posix":
        mode = stat.S_IMODE(env_path.stat().st_mode)
        if mode & (stat.S_IRWXG | stat.S_IRWXO):
            errors.append(f"{env_path} permissions must be 0600 (currently {mode:04o})")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", type=Path, default=Path(".env"))
    args = parser.parse_args()
    if not args.env.is_file():
        print(f"PREFLIGHT FAILED: missing {args.env}")
        return 1
    errors = validate(parse_env(args.env), args.env)
    if errors:
        print("PREFLIGHT FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PREFLIGHT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
