"""TOTP two-factor authentication module.

Standards-compliant TOTP (RFC 6238) with QR code provisioning.
"""

import base64
import hashlib
import hmac
import os
import struct
import time
from typing import Optional


def generate_secret(length: int = 20) -> str:
    """Generate a new TOTP secret (base32 encoded)."""
    return base64.b32encode(os.urandom(length)).decode("utf-8").rstrip("=")


def get_totp_token(secret: str, interval: int = 30, digits: int = 6) -> str:
    # Decode base32 secret (add padding if needed)
    padding = 8 - len(secret) % 8
    if padding != 8:
        secret = secret + "=" * padding
    key = base64.b32decode(secret)
    
    # Calculate counter
    counter = int(time.time() // interval)
    counter_bytes = struct.pack(">Q", counter)
    
    # HMAC-SHA1
    hmac_result = hmac.new(key, counter_bytes, hashlib.sha1).digest()
    
    # Dynamic truncation
    offset = hmac_result[-1] & 0x0F
    binary = struct.unpack(">I", hmac_result[offset:offset + 4])[0] & 0x7FFFFFFF
    
    token = str(binary % (10 ** digits)).zfill(digits)
    return token


def verify_totp(secret: str, token: str, window: int = 1) -> bool:
    """Verify TOTP token within time window."""
    if not secret or not token:
        return False
    
    current = int(time.time() // 30)
    for offset in range(-window, window + 1):
        test_time = (current + offset) * 30
        # Decode with correct padding
        pad = 8 - len(secret) % 8
        decoded_secret = secret + "=" * pad if pad != 8 else secret
        key = base64.b32decode(decoded_secret)
        counter_bytes = struct.pack(">Q", test_time // 30)
        hmac_result = hmac.new(key, counter_bytes, hashlib.sha1).digest()
        off = hmac_result[-1] & 0x0F
        binary = struct.unpack(">I", hmac_result[off:off + 4])[0] & 0x7FFFFFFF
        generated = str(binary % 1_000_000).zfill(6)
        if hmac.compare_digest(generated, token):
            return True
    return False


def generate_provisioning_uri(secret: str, email: str, issuer: str = "KAgent") -> str:
    """Generate otpauth:// URI for QR code provisioning."""
    return f"otpauth://totp/{issuer}:{email}?secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30"


# ═══════════════════════════════════════════════════════════════════════
# FastAPI routes (add to auth-routes.ts equivalent in Python)
# ═══════════════════════════════════════════════════════════════════════

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

totp_app = FastAPI(title="KAgent TOTP", version="0.8.0")


class EnableTOTPRequest(BaseModel):
    account_id: str
    token: str


class VerifyTOTPRequest(BaseModel):
    account_id: str
    token: str


# In-memory store (replace with DB in production)
_totp_secrets: dict[str, str] = {}


@totp_app.post("/v1/auth/totp/setup")
async def setup_totp(account_id: str):
    secret = generate_secret()
    _totp_secrets[account_id] = secret
    uri = generate_provisioning_uri(secret, account_id)
    return {
        "secret": secret,
        "provisioning_uri": uri,
        "message": "Scan QR code with authenticator app, then verify with /v1/auth/totp/verify",
    }


@totp_app.post("/v1/auth/totp/verify")
async def verify_totp_endpoint(req: VerifyTOTPRequest):
    secret = _totp_secrets.get(req.account_id)
    if not secret:
        raise HTTPException(404, "TOTP not set up for this account")
    
    if verify_totp(secret, req.token):
        return {"status": "verified", "message": "TOTP enabled"}
    else:
        raise HTTPException(401, "Invalid TOTP token")


@totp_app.post("/v1/auth/totp/validate")
async def validate_totp(req: VerifyTOTPRequest):
    """Validate TOTP token during login."""
    secret = _totp_secrets.get(req.account_id)
    if not secret:
        raise HTTPException(404, "TOTP not configured")
    
    if verify_totp(secret, req.token):
        return {"status": "valid"}
    else:
        raise HTTPException(401, "Invalid TOTP token")
