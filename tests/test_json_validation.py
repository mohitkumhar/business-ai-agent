from __future__ import annotations

import os
import sys
import pytest
import jwt
from datetime import datetime, timedelta

class DummyCursor:
    def execute(self, *args, **kwargs):
        pass
    def fetchone(self):
        return None
    def fetchall(self):
        return []
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass

class DummyConnection:
    def cursor(self):
        return DummyCursor()
    def commit(self):
        pass
    def close(self):
        pass
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass

@pytest.fixture(scope="session")
def agent_app_module():
    os.environ.setdefault("GROQ_API_KEY", "test-key")
    os.environ.setdefault("OPENROUTER_API_KEY", "test-openrouter-key")
    os.environ.setdefault("JWT_SECRET", "test-secret")
    os.environ["USE_IN_MEMORY_CHECKPOINTER"] = "true"

    from agent_code import app as agent_app
    agent_app.app.config.update(TESTING=True, RATELIMIT_ENABLED=False, SECRET_KEY="test-secret")
    return agent_app

@pytest.fixture()
def agent_client(agent_app_module):
    return agent_app_module.app.test_client()

@pytest.fixture()
def agent_auth_headers(agent_app_module):
    token = jwt.encode(
        {
            "user_id": "user-1",
            "business_id": "business-1",
            "exp": datetime.utcnow() + timedelta(hours=1),
        },
        agent_app_module.app.config["SECRET_KEY"],
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="session")
def app_main_module():
    os.environ.setdefault("GROQ_API_KEY", "test-key")
    os.environ.setdefault("OPENROUTER_API_KEY", "test-openrouter-key")
    os.environ.setdefault("JWT_SECRET", "test-secret")
    os.environ["USE_IN_MEMORY_CHECKPOINTER"] = "true"

    # Mock psycopg2/psycopg connection before app_main loads
    import db_config
    db_config.get_db_connection = lambda: DummyConnection()



    from agent_code import app_main
    app_main.app.config.update(TESTING=True, RATELIMIT_ENABLED=False, SECRET_KEY="test-secret")
    return app_main

@pytest.fixture()
def app_main_client(app_main_module):
    return app_main_module.app.test_client()

@pytest.fixture()
def web_client():
    from web import app as web_app
    web_app.app.config.update(TESTING=True)
    return web_app.app.test_client()

@pytest.fixture(autouse=True)
def disable_limiter(agent_app_module, app_main_module):
    if hasattr(agent_app_module, "limiter"):
        agent_app_module.limiter.enabled = False
    if hasattr(app_main_module, "limiter"):
        app_main_module.limiter.enabled = False

INVALID_PAYLOADS = [
    (None, "application/json"),
    ("[]", "application/json"),
    ("[1, 2, 3]", "application/json"),
    ('"string"', "application/json"),
    ("true", "application/json"),
    ("123", "application/json"),
    ("{invalid_json", "application/json"),
]

# --- Test agent_code/app.py Endpoints ---

@pytest.mark.parametrize("payload,content_type", INVALID_PAYLOADS)
def test_app_auth_signup_invalid_json(agent_client, payload, content_type):
    response = agent_client.post("/api/auth/signup", data=payload, content_type=content_type)
    assert response.status_code == 400
    assert "Invalid or missing JSON payload" in response.get_json()["message"]

@pytest.mark.parametrize("payload,content_type", INVALID_PAYLOADS)
def test_app_auth_login_invalid_json(agent_client, payload, content_type):
    response = agent_client.post("/api/auth/login", data=payload, content_type=content_type)
    assert response.status_code == 400
    assert "Invalid or missing JSON payload" in response.get_json()["message"]

@pytest.mark.parametrize("payload,content_type", INVALID_PAYLOADS)
def test_app_onboarding_invalid_json(agent_client, payload, content_type):
    response = agent_client.post("/api/v1/onboarding", data=payload, content_type=content_type)
    assert response.status_code == 400
    assert "Invalid or missing JSON payload" in response.get_json()["error"]

@pytest.mark.parametrize("payload,content_type", INVALID_PAYLOADS)
def test_app_chat_send_invalid_json(agent_client, agent_auth_headers, payload, content_type):
    response = agent_client.post("/api/chat/send", headers=agent_auth_headers, data=payload, content_type=content_type)
    assert response.status_code == 400
    assert "Invalid or missing JSON payload" in response.get_json()["error"]

@pytest.mark.parametrize("payload,content_type", INVALID_PAYLOADS)
def test_app_chat_conversation_put_invalid_json(agent_client, agent_auth_headers, payload, content_type):
    response = agent_client.put("/api/chat/conversations/conv-123", headers=agent_auth_headers, data=payload, content_type=content_type)
    assert response.status_code == 400
    assert "Invalid or missing JSON payload" in response.get_json()["error"]

@pytest.mark.parametrize("payload,content_type", INVALID_PAYLOADS)
def test_app_chat_conversation_messages_post_invalid_json(agent_client, agent_auth_headers, payload, content_type):
    response = agent_client.post("/api/chat/conversations/conv-123/messages", headers=agent_auth_headers, data=payload, content_type=content_type)
    assert response.status_code == 400
    assert "Invalid or missing JSON payload" in response.get_json()["error"]

@pytest.mark.parametrize("payload,content_type", INVALID_PAYLOADS)
def test_app_telegram_webhook_invalid_json(agent_client, payload, content_type):
    response = agent_client.post("/api/v1/telegram/webhook", data=payload, content_type=content_type)
    assert response.status_code == 400
    assert "Invalid or missing JSON payload" in response.get_json()["error"]


# --- Test agent_code/app_main.py Endpoints ---

@pytest.mark.parametrize("payload,content_type", INVALID_PAYLOADS)
def test_app_main_billing_analyze_all_invalid_json(app_main_client, payload, content_type):
    response = app_main_client.post("/api/v1/billing/analyze-all", data=payload, content_type=content_type)
    assert response.status_code == 400
    assert "Invalid or missing JSON payload" in response.get_json()["error"]

@pytest.mark.parametrize("payload,content_type", INVALID_PAYLOADS)
def test_app_main_whatsapp_webhook_invalid_json(app_main_client, payload, content_type):
    response = app_main_client.post("/api/v1/whatsapp/webhook", data=payload, content_type=content_type)
    assert response.status_code == 400
    assert "Invalid or missing JSON payload" in response.get_json()["error"]

@pytest.mark.parametrize("payload,content_type", INVALID_PAYLOADS)
def test_app_main_telegram_webhook_invalid_json(app_main_client, payload, content_type):
    response = app_main_client.post("/api/v1/telegram/webhook", data=payload, content_type=content_type)
    assert response.status_code == 400
    assert "Invalid or missing JSON payload" in response.get_json()["error"]

@pytest.mark.parametrize("payload,content_type", INVALID_PAYLOADS)
def test_app_main_escalate_invalid_json(app_main_client, payload, content_type):
    response = app_main_client.post("/api/v1/escalate", data=payload, content_type=content_type)
    assert response.status_code == 400
    assert "Invalid or missing JSON payload" in response.get_json()["error"]

@pytest.mark.parametrize("payload,content_type", INVALID_PAYLOADS)
def test_app_main_onboarding_invalid_json(app_main_client, payload, content_type):
    response = app_main_client.post("/api/v1/onboarding", data=payload, content_type=content_type)
    assert response.status_code == 400
    assert "Invalid or missing JSON payload" in response.get_json()["error"]

@pytest.mark.parametrize("payload,content_type", INVALID_PAYLOADS)
def test_app_main_chat_send_invalid_json(app_main_client, payload, content_type):
    response = app_main_client.post("/api/chat/send", data=payload, content_type=content_type)
    assert response.status_code == 400
    assert "Invalid or missing JSON payload" in response.get_json()["error"]


# --- Test web/app.py Endpoints ---

@pytest.mark.parametrize("payload,content_type", INVALID_PAYLOADS)
def test_web_create_conversation_invalid_json(web_client, payload, content_type):
    response = web_client.post("/api/chat/conversations", data=payload, content_type=content_type)
    assert response.status_code == 400
    assert "Invalid or missing JSON payload" in response.get_json()["error"]

@pytest.mark.parametrize("payload,content_type", INVALID_PAYLOADS)
def test_web_chat_send_invalid_json(web_client, payload, content_type):
    response = web_client.post("/api/chat/send", data=payload, content_type=content_type)
    assert response.status_code == 400
    assert "Invalid or missing JSON payload" in response.get_json()["error"]
