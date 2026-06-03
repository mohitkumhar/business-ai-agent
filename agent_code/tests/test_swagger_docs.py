from __future__ import annotations


DOCUMENTED_OPERATIONS = [
    ("/", "get"),
    ("/health", "get"),
    ("/metrics", "get"),
    ("/api/auth/signup", "post"),
    ("/api/auth/login", "post"),
    ("/api/v1/onboarding", "post"),
    ("/api/v1/query", "post"),
    ("/api/v1/whatsapp/webhook", "get"),
    ("/api/v1/whatsapp/webhook", "post"),
    ("/api/v1/telegram/webhook", "post"),
    ("/api/chat/send", "post"),
    ("/api/v1/import/transactions", "post"),
    ("/api/v1/import/notebook", "post"),
    ("/api/v1/import/confirm-notebook", "post"),
    ("/api/dashboard/forecast", "get"),
    ("/api/dashboard/categories", "get"),
    ("/api/dashboard/financial-overview", "get"),
    ("/api/dashboard/revenue-vs-expense", "get"),
    ("/api/dashboard/sales-trend", "get"),
    ("/api/dashboard/recent-transactions", "get"),
    ("/api/dashboard/export-csv", "get"),
    ("/api/dashboard/summary-sql", "get"),
    ("/api/dashboard/alerts-list", "get"),
    ("/api/dashboard/business-info", "get"),
    ("/api/dashboard/sales-target", "get"),
    ("/api/dashboard/alerts-by-severity", "get"),
    ("/api/dashboard/health-scores", "get"),
    ("/api/dashboard/top-products", "get"),
    ("/api/dashboard/employee-stats", "get"),
]


def _operation(spec: dict, path: str, method: str) -> dict:
    return spec["paths"][path][method]


def test_swagger_ui_and_spec_document_core_backend_routes(client):
    ui_response = client.get("/apidocs", follow_redirects=True)
    assert ui_response.status_code == 200
    assert b"swagger" in ui_response.data.lower()

    spec_response = client.get("/apispec_1.json")
    assert spec_response.status_code == 200

    spec = spec_response.get_json()
    assert spec["info"]["title"] == "ProfitPilot Flask API"
    assert spec["swagger"] == "2.0"
    assert spec["securityDefinitions"]["BearerAuth"] == {
        "type": "apiKey",
        "name": "Authorization",
        "in": "header",
        "description": "Use a JWT bearer token, for example: Bearer <token>",
    }

    documented = [
        _operation(spec, path, method)
        for path, method in DOCUMENTED_OPERATIONS
        if path in spec["paths"] and method in spec["paths"][path]
    ]
    assert len(documented) >= 20
    assert {"Auth", "Chat", "Dashboard", "Import", "System", "V1"} <= {
        tag["name"] for tag in spec["tags"]
    }

    login = _operation(spec, "/api/auth/login", "post")
    body_schema = next(
        param["schema"] for param in login["parameters"] if param["in"] == "body"
    )
    assert body_schema["example"]["email"] == "owner@example.com"
    assert {"400", "401", "500"} <= set(login["responses"])

    chat = _operation(spec, "/api/chat/send", "post")
    assert chat["security"] == [{"BearerAuth": []}]
    assert chat["produces"] == ["text/event-stream"]
    assert (
        chat["parameters"][0]["schema"]["example"]["message"]
        == "Show this month revenue"
    )
    assert {"400", "401", "500"} <= set(chat["responses"])

    import_transactions = _operation(spec, "/api/v1/import/transactions", "post")
    assert import_transactions["consumes"] == ["multipart/form-data"]
    assert import_transactions["security"] == [{"BearerAuth": []}]
    assert any(
        param["name"] == "file" and param["type"] == "file"
        for param in import_transactions["parameters"]
    )
    assert {"400", "401", "500"} <= set(import_transactions["responses"])

    dashboard_summary = _operation(spec, "/api/dashboard/summary-sql", "get")
    assert dashboard_summary["security"] == [{"BearerAuth": []}]
    assert any(
        param["name"] == "period" and param["default"] == "this_month"
        for param in dashboard_summary["parameters"]
    )
    assert {"400", "401", "500"} <= set(dashboard_summary["responses"])
