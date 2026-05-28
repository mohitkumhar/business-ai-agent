from __future__ import annotations

import ast
from pathlib import Path


APP_MAIN_PATH = Path(__file__).resolve().parents[1] / "app_main.py"


def _get_function(name: str) -> tuple[ast.FunctionDef, str]:
    source = APP_MAIN_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node, ast.get_source_segment(source, node) or ""
    raise AssertionError(f"Function {name} not found")


def test_app_main_revenue_vs_expense_requires_token_decorator():
    route_node, route_source = _get_function("api_revenue_vs_expense")

    decorators = [decorator.id for decorator in route_node.decorator_list if isinstance(decorator, ast.Name)]
    assert "token_required" in decorators
    assert "bid = get_current_business_id()" in route_source


def test_app_main_revenue_vs_expense_filters_by_business_id():
    _, route_source = _get_function("api_revenue_vs_expense")

    assert "WHERE business_id = %s AND transaction_date >= %s" in route_source
    assert "(bid, cutoff)" in route_source
