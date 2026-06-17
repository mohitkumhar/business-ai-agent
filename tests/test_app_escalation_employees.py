from __future__ import annotations

import os
import re
from datetime import datetime, timedelta

import jwt
import pytest


@pytest.fixture(scope="module")
def app_module():
    os.environ.setdefault("GROQ_API_KEY", "test-key")
    os.environ.setdefault("OPENROUTER_API_KEY", "test-openrouter-key")
    os.environ.setdefault("JWT_SECRET", "test-secret")
    os.environ["USE_IN_MEMORY_CHECKPOINTER"] = "true"

    from agent_code import app

    app.app.config.update(
        TESTING=True, RATELIMIT_ENABLED=False, SECRET_KEY="test-secret"
    )
    return app


@pytest.fixture()
def client(app_module):
    return app_module.app.test_client()


@pytest.fixture()
def auth_headers(app_module):
    token = jwt.encode(
        {
            "user_id": "user-1",
            "business_id": "business-1",
            "exp": datetime.utcnow() + timedelta(hours=1),
        },
        app_module.app.config["SECRET_KEY"],
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


# ── Employees ──


def test_employees_returns_fallback_on_github_failure(client, monkeypatch):
    def fail_github(*args, **kwargs):
        raise RuntimeError("github API unreachable")

    monkeypatch.setattr("agent_code.app.requests.get", fail_github)
    monkeypatch.setattr("agent_code.app.get_assigned_counts", lambda: {})

    response = client.get("/api/v1/employees")

    assert response.status_code == 500
    payload = response.get_json()
    assert payload["code"] == "employees_unavailable"
    assert "internal server error" in payload["error"].lower()
    assert re.fullmatch(r"[0-9a-f]{32}", payload["request_id"])


def test_employees_sanitizes_bad_request_id(client, monkeypatch):
    def fail_github(*args, **kwargs):
        raise RuntimeError("github token leaked")

    monkeypatch.setattr("agent_code.app.requests.get", fail_github)
    monkeypatch.setattr("agent_code.app.get_assigned_counts", lambda: {})

    response = client.get(
        "/api/v1/employees",
        headers={"X-Request-ID": "bad/request-id"},
    )

    payload = response.get_json()
    assert response.status_code == 500
    assert re.fullmatch(r"[0-9a-f]{32}", payload["request_id"])
    assert payload["request_id"] != "bad/request-id"
    assert "github token" not in response.get_data(as_text=True)


def test_employees_uses_provided_request_id(client, monkeypatch):
    def fail_github(*args, **kwargs):
        raise RuntimeError("some error")

    monkeypatch.setattr("agent_code.app.requests.get", fail_github)
    monkeypatch.setattr("agent_code.app.get_assigned_counts", lambda: {})

    response = client.get(
        "/api/v1/employees",
        headers={"X-Request-ID": "req-employees-test"},
    )

    payload = response.get_json()
    assert response.status_code == 500
    assert payload["request_id"] == "req-employees-test"


def test_employees_fallback_on_github_non_200(client, monkeypatch):
    class FakeResponse:
        status_code = 403

    monkeypatch.setattr("agent_code.app.requests.get", lambda *a, **kw: FakeResponse())
    monkeypatch.setattr("agent_code.app.get_assigned_counts", lambda: {"engineer_a": 3})

    response = client.get("/api/v1/employees")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["degraded"] is True
    assert any(e["login"] == "engineer_a" for e in payload["employees"])
    eng_a = next(e for e in payload["employees"] if e["login"] == "engineer_a")
    assert eng_a["assigned_issues"] == 3


# ── Escalate ──


def test_escalate_requires_auth(client, monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Slack code must not run before auth")

    monkeypatch.setattr("agent_code.app.increment_assigned_count", fail_if_called)

    response = client.post(
        "/api/v1/escalate",
        json={"query": "post this to Slack", "summary": "untrusted input"},
    )

    assert response.status_code == 401
    assert response.get_json()["message"] == "Authorization header is required"


def test_escalate_validates_json(client, auth_headers):
    response = client.post(
        "/api/v1/escalate",
        data="not json",
        content_type="application/json",
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid or missing JSON payload"
