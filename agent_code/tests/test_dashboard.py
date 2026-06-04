from __future__ import annotations

from datetime import date
from decimal import Decimal


def test_dashboard_categories_requires_authentication(client):
    response = client.get("/api/dashboard/categories")

    assert response.status_code == 401
    assert response.get_json()["message"] == "Authorization header is required"


def test_dashboard_categories_returns_distinct_categories(client, app_module, auth_headers, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "execute_read_query_params",
        lambda *args, **kwargs: [{"category": "Sales"}, {"category": "Rent"}],
    )

    response = client.get("/api/dashboard/categories", headers=auth_headers)

    assert response.status_code == 200
    assert response.get_json() == {"categories": ["Sales", "Rent"]}


def test_dashboard_summary_computes_period_changes(client, app_module, auth_headers, monkeypatch):
    rows = iter(
        [
            [{"rev": 2000, "exp": 500, "txns": 8}],
            [{"count": 3}],
            [{"rev": 1000, "exp": 400, "txns": 4}],
            [{"count": 1}],
        ]
    )
    monkeypatch.setattr(app_module, "execute_read_query_params", lambda *args, **kwargs: next(rows))

    response = client.get("/api/dashboard/summary-sql?period=last_7_days", headers=auth_headers)

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["total_revenue"] == 2000
    assert payload["net_profit"] == 1500
    assert payload["revenue_change"] == 100
    assert payload["transactions_change"] == 100


def test_alerts_by_severity_returns_chart_payload(client, app_module, auth_headers, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "execute_read_query_params",
        lambda *args, **kwargs: [{"severity": "High", "cnt": 2}, {"severity": "Low", "cnt": 1}],
    )

    response = client.get("/api/dashboard/alerts-by-severity", headers=auth_headers)

    assert response.status_code == 200
    assert response.get_json() == {"labels": ["High", "Low"], "data": [2, 1]}


def test_dashboard_export_csv_downloads_filtered_transactions(client, app_module, auth_headers, monkeypatch):
    captured = {}

    def fake_read_query(sql, params):
        captured["sql"] = sql
        captured["params"] = params
        return [
            {
                "transaction_id": 7,
                "transaction_date": date(2026, 5, 20),
                "type": "Revenue",
                "category": "Sales",
                "amount": Decimal("1250.50"),
                "description": "May invoice",
            }
        ]

    monkeypatch.setattr(app_module, "execute_read_query_params", fake_read_query)

    response = client.get("/api/dashboard/export-csv?period=last_7_days", headers=auth_headers)

    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "attachment; filename=profitpilot_export_last_7_days_" in response.headers["Content-Disposition"]
    assert response.get_data(as_text=True).splitlines() == [
        "transaction_id,transaction_date,type,category,amount,description",
        "7,2026-05-20,Revenue,Sales,1250.50,May invoice",
    ]
    assert "transaction_date BETWEEN %s AND %s" in captured["sql"]
    assert captured["params"][0] == "business-1"


def test_dashboard_export_csv_resolves_business_from_email(client, app_module, monkeypatch):
    calls = []

    def fake_read_query(sql, params):
        calls.append((sql, params))
        if "FROM users" in sql:
            return [{"business_id": "business-email"}]
        return []

    monkeypatch.setattr(app_module, "execute_read_query_params", fake_read_query)

    response = client.get("/api/dashboard/export-csv?period=this_month&email=owner@example.com")

    assert response.status_code == 200
    assert response.get_data(as_text=True).splitlines() == [
        "transaction_id,transaction_date,type,category,amount,description",
    ]
    assert calls[0][1] == ("owner@example.com",)
    assert calls[1][1][0] == "business-email"
