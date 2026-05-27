from __future__ import annotations

from .helpers import FakeConnection, FakeCursor


def test_onboarding_requires_business_name_and_email(client):
    response = client.post("/api/v1/onboarding", json={"business_name": "Pilot Store"})

    assert response.status_code == 400
    assert response.get_json()["error"] == "Missing fields"


def test_onboarding_creates_business_and_user(client, app_module, monkeypatch):
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    monkeypatch.setattr(app_module, "get_db_connection", lambda: connection)

    response = client.post(
        "/api/v1/onboarding",
        json={
            "business_name": "Pilot Store",
            "business_category": "Retail",
            "full_name": "Owner",
            "email": "OWNER@EXAMPLE.COM",
        },
    )

    payload = response.get_json()
    assert response.status_code == 201
    assert payload["success"] is True
    assert payload["business_id"]
    assert connection.committed is True
    assert connection.closed is True
    assert len(cursor.executed) == 2
