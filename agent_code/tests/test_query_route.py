from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt


def _bearer_token(app_module, business_id="business-token"):
    token = jwt.encode(
        {
            "user_id": "user-token",
            "business_id": business_id,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        app_module.app.config["SECRET_KEY"],
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def test_query_route_streams_sse_for_dashboard_proxy(client, app_module, monkeypatch):
    captured = {}

    def fake_stream_agent_sse_lines(query, thread_id, business_id, on_chain_intent=None):
        captured["query"] = query
        captured["thread_id"] = thread_id
        captured["business_id"] = business_id
        captured["has_intent_callback"] = callable(on_chain_intent)
        yield 'data: {"type":"token","content":"ok"}\n\n'

    monkeypatch.setattr(app_module, "stream_agent_sse_lines", fake_stream_agent_sse_lines)

    response = client.post(
        "/api/v1/query",
        query_string={
            "input-query": "How are sales?",
            "thread-id": "thread-1",
            "business-id": "business-1",
        },
    )

    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    assert response.headers["Cache-Control"] == "no-cache, no-transform"
    assert response.headers["X-Accel-Buffering"] == "no"
    assert response.get_data(as_text=True) == 'data: {"type":"token","content":"ok"}\n\n'
    assert captured == {
        "query": "How are sales?",
        "thread_id": "thread-1",
        "business_id": "business-1",
        "has_intent_callback": True,
    }


def test_query_route_requires_dashboard_proxy_params(client):
    response = client.post("/api/v1/query", query_string={"input-query": "Hello"})

    assert response.status_code == 400
    assert response.get_json() == {"is_error": True, "error": "thread-id is required"}


def test_query_route_derives_business_context_from_jwt(client, app_module, monkeypatch):
    captured = {}

    def fake_stream_agent_sse_lines(query, thread_id, business_id, on_chain_intent=None):
        captured["business_id"] = business_id
        yield 'data: {"type":"token","content":"ok"}\n\n'

    monkeypatch.setattr(app_module, "stream_agent_sse_lines", fake_stream_agent_sse_lines)

    response = client.post(
        "/api/v1/query",
        query_string={
            "input-query": "How are sales?",
            "thread-id": "thread-1",
        },
        headers=_bearer_token(app_module, business_id="business-from-token"),
    )

    assert response.status_code == 200
    assert captured["business_id"] == "business-from-token"


def test_query_route_prefers_jwt_business_context_over_query_param(client, app_module, monkeypatch):
    captured = {}

    def fake_stream_agent_sse_lines(query, thread_id, business_id, on_chain_intent=None):
        captured["business_id"] = business_id
        yield 'data: {"type":"token","content":"ok"}\n\n'

    monkeypatch.setattr(app_module, "stream_agent_sse_lines", fake_stream_agent_sse_lines)

    response = client.post(
        "/api/v1/query",
        query_string={
            "input-query": "How are sales?",
            "thread-id": "thread-1",
            "business-id": "business-from-query",
        },
        headers=_bearer_token(app_module, business_id="business-from-token"),
    )

    assert response.status_code == 200
    assert captured["business_id"] == "business-from-token"
