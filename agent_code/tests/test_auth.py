from __future__ import annotations

import bcrypt

from .helpers import FakeConnection, FakeCursor


def test_signup_requires_all_fields(client):
    response = client.post("/api/auth/signup", json={"email": "owner@example.com"})

    assert response.status_code == 400
    assert response.get_json()["message"] == "All fields are required"


def test_signup_rejects_existing_user(client, app_module, monkeypatch):
    cursor = FakeCursor(fetchone_values=[("existing-user",)])
    monkeypatch.setattr(app_module, "get_db_connection", lambda: FakeConnection(cursor))

    response = client.post(
        "/api/auth/signup",
        json={
            "email": "owner@example.com",
            "password": "secret123",
            "name": "Owner",
            "business_name": "Pilot Store",
        },
    )

    assert response.status_code == 409
    assert response.get_json()["message"] == "User already exists"


def test_login_requires_email_and_password(client):
    response = client.post("/api/auth/login", json={"email": "owner@example.com"})

    assert response.status_code == 400
    assert response.get_json()["message"] == "Email and password required"


def test_login_returns_token_for_valid_credentials(client, app_module, monkeypatch):
    password_hash = bcrypt.hashpw(b"secret123", bcrypt.gensalt()).decode("utf-8")
    cursor = FakeCursor(
        fetchone_values=[
            {
                "user_id": "user-1",
                "business_id": "business-1",
                "name": "Owner",
                "password_hash": password_hash,
            }
        ]
    )
    monkeypatch.setattr(app_module, "get_db_connection", lambda: FakeConnection(cursor))

    response = client.post(
        "/api/auth/login",
        json={"email": "owner@example.com", "password": "secret123"},
    )

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["business_id"] == "business-1"
    assert payload["token"]
