from __future__ import annotations

import ast
import importlib
import os
import re
from pathlib import Path

import pytest


APP_MAIN = Path(__file__).resolve().parents[1] / "agent_code" / "app_main.py"


def _decorator_name(decorator: ast.expr) -> str:
    if isinstance(decorator, ast.Name):
        return decorator.id
    if isinstance(decorator, ast.Call):
        return _decorator_name(decorator.func)
    if isinstance(decorator, ast.Attribute):
        return decorator.attr
    return ""


def _function_named(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} was not found")


def test_app_main_revenue_vs_expense_requires_token_guard():
    tree = ast.parse(APP_MAIN.read_text())
    route = _function_named(tree, "api_revenue_vs_expense")

    decorators = {_decorator_name(decorator) for decorator in route.decorator_list}

    assert "route" in decorators
    assert "token_required" in decorators


def test_app_main_revenue_vs_expense_query_is_tenant_scoped():
    source = APP_MAIN.read_text()

    assert "bid = get_current_business_id()" in source
    assert "WHERE business_id = %s AND transaction_date BETWEEN %s AND %s" in source
    assert "(bid, start_date, end_date)" in source


def test_app_main_employees_error_response_is_client_safe():
    source = APP_MAIN.read_text()

    assert '"code": "employees_unavailable"' in source
    assert '"request_id": request_id' in source
    assert "SAFE_INTERNAL_ERROR_MESSAGE" in source
    assert "return internal_error_response(exc)" not in source[
        source.index("def get_employees") : source.index('@app.route("/api/v1/escalate"')
    ]


def test_app_main_employees_runtime_error_response_is_client_safe(monkeypatch):
    os.environ.setdefault("JWT_SECRET", "unit-test-jwt-secret")

    try:
        app_main = importlib.import_module("agent_code.app_main")
    except Exception as exc:
        pytest.skip(f"backend app dependencies unavailable: {exc}")

    def fail_github_request(*args, **kwargs):
        raise RuntimeError("github token leaked in raw exception")

    monkeypatch.setattr(app_main.requests, "get", fail_github_request)
    monkeypatch.setattr(app_main, "get_assigned_counts", lambda: {})

    app_main.app.config.update(TESTING=True)
    response = app_main.app.test_client().get(
        "/api/v1/employees",
        headers={"X-Request-Id": "req-employees-test"},
    )

    assert response.status_code == 500
    assert response.get_json() == {
        "error": app_main.SAFE_INTERNAL_ERROR_MESSAGE,
        "code": "employees_unavailable",
        "request_id": "req-employees-test",
    }
    assert "github token" not in response.get_data(as_text=True)


def test_app_main_employees_invalid_request_id_is_sanitized(monkeypatch):
    os.environ.setdefault("JWT_SECRET", "unit-test-jwt-secret")

    try:
        app_main = importlib.import_module("agent_code.app_main")
    except Exception as exc:
        pytest.skip(f"backend app dependencies unavailable: {exc}")

    def fail_github_request(*args, **kwargs):
        raise RuntimeError("github token leaked in raw exception")

    monkeypatch.setattr(app_main.requests, "get", fail_github_request)
    monkeypatch.setattr(app_main, "get_assigned_counts", lambda: {})

    app_main.app.config.update(TESTING=True)
    response = app_main.app.test_client().get(
        "/api/v1/employees",
        headers={"X-Request-Id": "bad/request-id"},
    )

    payload = response.get_json()

    assert response.status_code == 500
    assert payload["request_id"] == response.headers["X-Request-ID"]
    assert re.fullmatch(r"[0-9a-f]{32}", payload["request_id"])
    assert payload["request_id"] != "bad/request-id"
    assert "github token" not in response.get_data(as_text=True)
