from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import jwt

DEFAULT_JWT_SECRET = "super-secret-business-key-2026"


@dataclass(frozen=True)
class AuthError(Exception):
    message: str
    status_code: int = 401


def require_jwt_secret(raw_secret: str | None) -> str:
    if not raw_secret:
        raise RuntimeError("JWT_SECRET must be set before starting the API")
    if raw_secret == DEFAULT_JWT_SECRET:
        raise RuntimeError("JWT_SECRET must not use the documented sample value")
    return raw_secret


def _extract_bearer_token(auth_header: str | None) -> str:
    if not auth_header:
        raise AuthError("Authorization header is required")

    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise AuthError("Authorization header must use Bearer token")

    return token.strip()


def decode_jwt_identity(auth_header: str | None, secret_key: str) -> dict[str, Any]:
    token = _extract_bearer_token(auth_header)

    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("Invalid authentication token") from exc

    user_id = payload.get("user_id")
    business_id = payload.get("business_id")
    if not user_id or not business_id:
        raise AuthError("Token is missing required identity claims")

    return {"user_id": str(user_id), "business_id": str(business_id)}
