from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from agent_code.auth import AuthError, DEFAULT_JWT_SECRET, decode_jwt_identity, require_jwt_secret


SECRET = "test-secret-with-at-least-32-bytes"


def test_require_jwt_secret_accepts_custom_secret():
    assert require_jwt_secret(SECRET) == SECRET


@pytest.mark.parametrize("raw_secret", [None, "", DEFAULT_JWT_SECRET])
def test_require_jwt_secret_rejects_missing_or_sample_secret(raw_secret):
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        require_jwt_secret(raw_secret)


def _token(payload):
    return jwt.encode(payload, SECRET, algorithm="HS256")


def test_decode_jwt_identity_accepts_valid_bearer_token():
    token = _token(
        {
            "user_id": "user-123",
            "business_id": "business-456",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        }
    )

    identity = decode_jwt_identity(f"Bearer {token}", SECRET)

    assert identity == {"user_id": "user-123", "business_id": "business-456"}


@pytest.mark.parametrize("auth_header", [None, "", "Basic abc", "Bearer "])
def test_decode_jwt_identity_rejects_missing_or_non_bearer_header(auth_header):
    with pytest.raises(AuthError) as exc:
        decode_jwt_identity(auth_header, SECRET)

    assert exc.value.status_code == 401


def test_decode_jwt_identity_rejects_invalid_signature():
    token = jwt.encode(
        {
            "user_id": "user-123",
            "business_id": "business-456",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        "wrong-secret-with-at-least-32-bytes",
        algorithm="HS256",
    )

    with pytest.raises(AuthError, match="Invalid authentication token"):
        decode_jwt_identity(f"Bearer {token}", SECRET)


def test_decode_jwt_identity_rejects_expired_token():
    token = _token(
        {
            "user_id": "user-123",
            "business_id": "business-456",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        }
    )

    with pytest.raises(AuthError, match="Token has expired"):
        decode_jwt_identity(f"Bearer {token}", SECRET)


@pytest.mark.parametrize(
    "payload",
    [
        {"business_id": "business-456"},
        {"user_id": "user-123"},
    ],
)
def test_decode_jwt_identity_requires_user_and_business_claims(payload):
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=5)
    token = _token(payload)

    with pytest.raises(AuthError, match="required identity claims"):
        decode_jwt_identity(f"Bearer {token}", SECRET)
