"""Minimal unit tests for TOTP module."""

from services.auth.src.totp import (
    generate_provisioning_uri,
    generate_secret,
    get_totp_token,
    verify_totp,
)


def test_generate_secret():
    secret = generate_secret()
    assert len(secret) > 0


def test_get_totp_token():
    secret = generate_secret()
    token = get_totp_token(secret)
    assert len(token) == 6
    assert token.isdigit()


def test_verify_totp():
    secret = generate_secret()
    token = get_totp_token(secret)
    assert verify_totp(secret, token) is True
    assert verify_totp(secret, "000000") is False


def test_generate_provisioning_uri():
    secret = generate_secret()
    uri = generate_provisioning_uri(secret, "user@example.com")
    assert uri.startswith("otpauth://totp/")
    assert secret in uri
