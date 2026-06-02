from __future__ import annotations

import ast
from pathlib import Path


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
