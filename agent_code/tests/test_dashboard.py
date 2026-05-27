from __future__ import annotations


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
