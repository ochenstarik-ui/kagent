"""Service-to-service authentication middleware.

Shared secret validation for internal services. Health endpoints are excluded.
"""

import hmac
import logging
import os

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

HEADER_NAME = "X-Service-Secret"
_HEALTH_PREFIXES = ("/health/live", "/health/ready")


class ServiceAuthMiddleware(BaseHTTPMiddleware):
    """Reject requests without a valid service secret.

    - Health endpoints are always allowed (compose healthchecks).
    - The secret is read from SERVICE_SECRET env var.
    - Comparison uses hmac.compare_digest (constant-time).
    - The secret value is never logged or included in error responses.
    """

    def __init__(self, app, *, secret: str | None = None) -> None:
        super().__init__(app)
        self._secret = secret or os.environ.get("SERVICE_SECRET", "")

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Health endpoints skip authentication
        if any(path.startswith(prefix) for prefix in _HEALTH_PREFIXES):
            return await call_next(request)

        # Require secret for all other endpoints
        if not self._secret:
            logger.error("SERVICE_SECRET not configured — rejecting request")
            return JSONResponse(
                status_code=401,
                content={"detail": "Service authentication not configured"},
            )

        provided = request.headers.get(HEADER_NAME, "")
        if not provided or not hmac.compare_digest(provided, self._secret):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing service credential"},
            )

        return await call_next(request)

import services.shared
