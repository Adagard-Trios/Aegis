"""
src/utils/auth.py

JWT bearer auth for the FastAPI backend.

Feature-flagged via the MEDVERSE_AUTH_ENABLED env var (default: false) so
the existing frontend (no auth) keeps working. Once the frontend is
updated to attach a bearer token, flip the flag to `true` and the
`/api/**` tree is protected.

CORS is also driven from here: MEDVERSE_CORS_ORIGINS is a comma-separated
list and defaults to localhost:3000 + 127.0.0.1:3000 so ports do not
need to change.
"""
from __future__ import annotations

import logging
import os
import time
from typing import List, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

try:
    import jwt  # PyJWT
    _JWT_AVAILABLE = True
except Exception:  # pragma: no cover
    _JWT_AVAILABLE = False


def auth_enabled() -> bool:
    return os.environ.get("MEDVERSE_AUTH_ENABLED", "false").lower() in ("1", "true", "yes")


def cors_origins() -> List[str]:
    raw = os.environ.get(
        "MEDVERSE_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    return [o.strip() for o in raw.split(",") if o.strip()]


def _secret() -> str:
    return os.environ.get("MEDVERSE_JWT_SECRET", "dev-insecure-change-me")


def _algorithm() -> str:
    return os.environ.get("MEDVERSE_JWT_ALG", "HS256")


def _expiry_seconds() -> int:
    return int(os.environ.get("MEDVERSE_JWT_EXPIRY_SECONDS", "3600"))


def create_access_token(subject: str, extra_claims: Optional[dict] = None) -> str:
    """Mint a signed JWT. Raises RuntimeError if PyJWT isn't installed."""
    if not _JWT_AVAILABLE:
        raise RuntimeError("PyJWT not installed. `pip install PyJWT`")
    now = int(time.time())
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + _expiry_seconds(),
        "iss": "medverse",
        **(extra_claims or {}),
    }
    token = jwt.encode(payload, _secret(), algorithm=_algorithm())
    if isinstance(token, bytes):  # PyJWT < 2 returns bytes
        token = token.decode("utf-8")
    return token


def _decode(token: str) -> dict:
    if not _JWT_AVAILABLE:
        raise RuntimeError("PyJWT not installed")
    return jwt.decode(token, _secret(), algorithms=[_algorithm()], issuer="medverse")


_bearer = HTTPBearer(auto_error=False)


async def require_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    """
    FastAPI dependency. When auth is disabled, returns an anonymous principal.
    When enabled, validates the bearer token and returns the JWT payload.
    """
    if not auth_enabled():
        return {"sub": "anonymous", "anonymous": True}

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return _decode(credentials.credentials)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_dev_credentials(username: str, password: str) -> bool:
    """Minimal dev login against env-supplied credentials."""
    expected_user = os.environ.get("MEDVERSE_DEV_USERNAME", "medverse")
    expected_pass = os.environ.get("MEDVERSE_DEV_PASSWORD", "medverse")
    return username == expected_user and password == expected_pass
