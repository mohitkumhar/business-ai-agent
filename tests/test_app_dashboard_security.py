"""Multitenancy / auth-isolation tests for the dashboard endpoints in agent_code/app.py.

These exercise the full Flask app, which pulls heavy dependencies (flask, langgraph,
prometheus_client, ...). The minimal CI image only installs ``pytest PyJWT openpyxl``,
so the whole module is skipped there and runs wherever the backend stack is installed.
"""
from __future__ import annotations

import os
import sys

import jwt
import pytest

# app.py validates JWT_SECRET at import time; provide a non-default value.
os.environ.setdefault("JWT_SECRET", "unit-test-jwt-secret")

try:
    import flask as _real_flask
    import flask.testing as _real_flask_testing  # noqa: F401 - cache submodule
    from agent_code import app as app_module
except Exception:  # pragma: no cover - exercised only on minimal CI
    pytest.skip("backend app dependencies unavailable", allow_module_level=True)

BUSINESS_A = "11111111-1111-1111-1111-111111111111"
BUSINESS_B = "22222222-2222-2222-2222-222222222222"


@pytest.fixture
def client(monkeypatch):
    # Another test in the suite replaces sys.modules["flask"] with a stub and
    # never restores it; ensure the real flask is in place for the test client.
    monkeypatch.setitem(sys.modules, "flask", _real_flask)
    monkeypatch.setitem(sys.modules, "flask.testing", _real_flask_testing)
    app_module.app.config.update(TESTING=True)
    return app_module.app.test_client()


def _token(business_id: str, user_id: str = "user-1") -> str:
    return jwt.encode(
        {"user_id": user_id, "business_id": business_id},
        app_module.app.config["SECRET_KEY"],
        algorithm="HS256",
    )


def _auth(business_id: str) -> dict:
    return {"Authorization": f"Bearer {_token(business_id)}"}


@pytest.fixture
def recorded_queries(monkeypatch):
    """Capture every (sql, params) sent to the DB layer; return no rows by default."""
    calls: list[tuple[str, object]] = []

    def fake_execute(sql, params=None):
        calls.append((sql, params))
        return []

    monkeypatch.setattr(app_module, "execute_read_query_params", fake_execute)
    return calls


def test_export_csv_requires_token(client, recorded_queries):
    resp = client.get("/api/dashboard/export-csv?period=this_month")
    assert resp.status_code == 401
    # No DB call should ever happen for an unauthenticated request.
    assert recorded_queries == []


def test_export_csv_ignores_email_fallback(client, recorded_queries):
    # The old email-query fallback must be gone: passing ?email= must not authenticate.
    resp = client.get("/api/dashboard/export-csv?period=this_month&email=victim@example.com")
    assert resp.status_code == 401
    assert recorded_queries == []


def test_export_csv_scoped_to_token_business(client, recorded_queries):
    resp = client.get("/api/dashboard/export-csv?period=this_month", headers=_auth(BUSINESS_A))
    assert resp.status_code == 200
    assert recorded_queries, "expected a DB query"
    sql, params = recorded_queries[-1]
    assert "business_id = %s" in sql
    # The business id comes from the token, never from a client-supplied value.
    assert params[0] == BUSINESS_A


def test_categories_filtered_by_business(client, recorded_queries):
    resp = client.get("/api/dashboard/categories", headers=_auth(BUSINESS_B))
    assert resp.status_code == 200
    sql, params = recorded_queries[-1]
    assert "business_id = %s" in sql
    assert params == (BUSINESS_B,)


def test_categories_requires_token(client, recorded_queries):
    resp = client.get("/api/dashboard/categories")
    assert resp.status_code == 401
    assert recorded_queries == []
