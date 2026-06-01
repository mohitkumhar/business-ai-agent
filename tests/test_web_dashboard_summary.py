from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import jwt

from web import app as web_app_module


def _token(business_id: str = "business-1") -> str:
    return jwt.encode(
        {
            "user_id": "user-1",
            "business_id": business_id,
            "exp": datetime.utcnow() + timedelta(minutes=15),
        },
        web_app_module.app.config["JWT_SECRET_KEY"],
        algorithm="HS256",
    )


def test_dashboard_summary_requires_bearer_token():
    web_app_module.app.config.update(TESTING=True)

    with web_app_module.app.test_client() as client:
        response = client.get("/api/dashboard/summary")

    assert response.status_code == 401
    assert response.get_json() == {"message": "Authorization header is required"}


def test_dashboard_summary_filters_queries_by_authenticated_business(monkeypatch):
    web_app_module.app.config.update(TESTING=True)
    captured_queries = []

    def fake_pg_query(sql, params=None):
        captured_queries.append((sql, params))
        if "FROM daily_transactions" in sql:
            return [
                {
                    "total_revenue": Decimal("200.50"),
                    "total_expenses": Decimal("50.25"),
                    "total_transactions": 3,
                }
            ]
        return [{"active_alerts": 2}]

    monkeypatch.setattr(web_app_module, "_pg_query", fake_pg_query)

    with web_app_module.app.test_client() as client:
        response = client.get(
            "/api/dashboard/summary",
            headers={"Authorization": f"Bearer {_token('business-123')}"},
        )

    assert response.status_code == 200
    assert response.get_json() == {
        "total_revenue": 200.5,
        "total_expenses": 50.25,
        "net_profit": 150.25,
        "total_transactions": 3,
        "active_alerts": 2,
    }
    assert len(captured_queries) == 2
    assert all("business_id = %s" in sql for sql, _ in captured_queries)
    assert all(params[0] == "business-123" for _, params in captured_queries)
