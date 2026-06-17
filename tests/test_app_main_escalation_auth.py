from __future__ import annotations

import os
from datetime import datetime, timedelta

import jwt
import pytest


@pytest.fixture(scope="module")
def app_main_module():
    os.environ.setdefault("GROQ_API_KEY", "test-key")
    os.environ.setdefault("OPENROUTER_API_KEY", "test-openrouter-key")
    os.environ.setdefault("JWT_SECRET", "test-secret")
    os.environ["USE_IN_MEMORY_CHECKPOINTER"] = "true"

    from agent_code import app_main

    app_main.app.config.update(
        TESTING=True, RATELIMIT_ENABLED=False, SECRET_KEY="test-secret"
    )
    return app_main


@pytest.fixture()
def client(app_main_module):
    return app_main_module.app.test_client()


@pytest.fixture()
def auth_headers(app_main_module):
    token = jwt.encode(
        {
            "user_id": "user-1",
            "business_id": "business-1",
            "exp": datetime.utcnow() + timedelta(hours=1),
        },
        app_main_module.app.config["SECRET_KEY"],
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def test_escalate_requires_auth_before_slack(client, monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Slack assignment count must not run before auth")

    monkeypatch.setattr("agent_code.app_main.increment_assigned_count", fail_if_called)

    response = client.post(
        "/api/v1/escalate",
        json={"query": "post this to Slack", "summary": "untrusted input"},
    )

    assert response.status_code == 401
    assert response.get_json()["message"] == "Authorization header is required"


def test_escalate_validates_json_after_auth(client, auth_headers):
    response = client.post(
        "/api/v1/escalate",
        data="not json",
        content_type="application/json",
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid or missing JSON payload"
