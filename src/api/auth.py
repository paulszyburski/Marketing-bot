import base64
import binascii
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

API_USERNAME = "admin"
PUBLIC_PATHS = {"/", "/website", "/website/", "/favicon.ico"}


def _credentials(authorization: str | None) -> tuple[str, str] | None:
    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.casefold() != "basic" or not token:
        return None

    try:
        decoded = base64.b64decode(token, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return None

    username, separator, password = decoded.partition(":")
    if not separator:
        return None
    return username, password


class ApiPasswordMiddleware(BaseHTTPMiddleware):
    """Require the configured API password for every HTTP endpoint."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path in PUBLIC_PATHS or request.url.path.startswith(
            "/website/static/"
        ):
            return await call_next(request)

        expected_password = os.getenv("API_PASSWORD")
        if not expected_password:
            return JSONResponse(
                status_code=503,
                content={"detail": "API_PASSWORD is not configured"},
            )

        credentials = _credentials(request.headers.get("Authorization"))
        authenticated = credentials is not None and secrets.compare_digest(
            credentials[0], API_USERNAME
        ) and secrets.compare_digest(credentials[1], expected_password)

        if not authenticated:
            # Do not send a WWW-Authenticate challenge. Browsers turn that header
            # into a native login dialog, while the website provides its own
            # accessible login page.
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid API credentials"},
            )

        return await call_next(request)
