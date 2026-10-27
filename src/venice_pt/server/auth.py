from __future__ import annotations

import os

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer(auto_error=False)

DEFAULT_API_TOKEN = os.environ.get("VENICE_API_TOKEN", "venice-secret-token")


def verify_token(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
) -> str:
    """Verifies Bearer token against environment or default token."""
    # If VENICE_AUTH_DISABLED is set, bypass authentication
    if os.environ.get("VENICE_AUTH_DISABLED", "false").lower() in ("true", "1"):
        return "anonymous"

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer authentication token",
        )

    if credentials.credentials != DEFAULT_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid authentication token",
        )

    return credentials.credentials
