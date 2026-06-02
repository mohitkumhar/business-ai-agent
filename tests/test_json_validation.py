from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
import pytest
from test_chat_history import app_module, client, auth_headers
from web import app as web_app_module

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
def app_main_module(tmp_path_factory):
    os.environ.setdefault("GROQ_API_KEY", "test-key")
    os.environ.setdefault("OPENROUTER_API_KEY", "test-openrouter-key")
    os.environ.setdefault("JWT_SECRET", "test-secret")
    os.environ["USE_IN_MEMORY_CHECKPOINTER"] = "true"
    
    agent_dir = Path(__file__).resolve().parents[1] / "agent_code"
    
    # Mock psycopg2 connection before app_main loads
    import db_config
    db_config.get_db_connection = lambda: DummyConnection()
    
    # Clear prometheus registry to prevent duplicate registration when importing app_main
    import prometheus_client
    for collector in list(prometheus_client.REGISTRY._collector_to_names.keys()):
        try:
            prometheus_client.REGISTRY.unregister(collector)
        except KeyError:
            pass

    module_path = agent_dir / "app_main.py"
    
    # Temporarily stub numpy if missing to avoid import failures
    if importlib.util.find_spec("numpy") is None:
        import types as std_types
        numpy = std_types.ModuleType("numpy")
        sys.modules["numpy"] = numpy

    # Dynamically load app_main.py with the duplicate Flask app definition commented out
    # so that all routes are registered on the same Flask app instance.
    import types
    module = types.ModuleType("profitpilot_agent_app_main")
    module.__file__ = str(module_path)
    sys.modules["profitpilot_agent_app_main"] = module

    source = module_path.read_text()
    occurrences = []
    start = 0
    while True:
        pos = source.find("app = Flask(__name__)", start)
        if pos == -1:
            break
        occurrences.append(pos)
        start = pos + 1

    if len(occurrences) >= 2:
        second_pos = occurrences[1]
        source = (
            source[:second_pos] +
            "# app = Flask(__name__)" +
            source[second_pos + len("app = Flask(__name__)"):]
        )

    # Rename only the second occurrence of api_dashboard_summary function to avoid Flask endpoint clash
    occurrences_fn = []
    start = 0
    while True:
        pos = source.find("def api_dashboard_summary():", start)
        if pos == -1:
            break
        occurrences_fn.append(pos)
        start = pos + 1

    if len(occurrences_fn) >= 2:
        second_fn_pos = occurrences_fn[1]
        source = (
            source[:second_fn_pos] +
            "def api_dashboard_summary_second():" +
            source[second_fn_pos + len("def api_dashboard_summary():"):]
        )

    exec(source, module.__dict__)
    module.app.config.update(TESTING=True, RATELIMIT_ENABLED=False, SECRET_KEY="test-secret")
    return module

@pytest.fixture(autouse=True)
def disable_limiter(app_module, app_main_module):
    if hasattr(app_module, "limiter"):
        app_module.limiter.enabled = False
    if hasattr(app_main_module, "limiter"):
        app_main_module.limiter.enabled = False

@pytest.fixture()
def app_main_client(app_main_module):
    return app_main_module.app.test_client()

@pytest.fixture()
def web_client():
    web_app_module.app.config.update(TESTING=True)
    return web_app_module.app.test_client()

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
def test_app_auth_signup_invalid_json(client, payload, content_type):
    response = client.post("/api/auth/signup", data=payload, content_type=content_type)
    assert response.status_code == 400
    assert "Invalid or missing JSON payload" in response.get_json()["message"]

@pytest.mark.parametrize("payload,content_type", INVALID_PAYLOADS)
def test_app_auth_login_invalid_json(client, payload, content_type):
    response = client.post("/api/auth/login", data=payload, content_type=content_type)
    assert response.status_code == 400
    assert "Invalid or missing JSON payload" in response.get_json()["message"]

@pytest.mark.parametrize("payload,content_type", INVALID_PAYLOADS)
def test_app_onboarding_invalid_json(client, payload, content_type):
    response = client.post("/api/v1/onboarding", data=payload, content_type=content_type)
    assert response.status_code == 400
    assert "Invalid or missing JSON payload" in response.get_json()["error"]

@pytest.mark.parametrize("payload,content_type", INVALID_PAYLOADS)
def test_app_chat_send_invalid_json(client, auth_headers, payload, content_type):
    response = client.post("/api/chat/send", headers=auth_headers, data=payload, content_type=content_type)
    assert response.status_code == 400
    assert "Invalid or missing JSON payload" in response.get_json()["error"]

@pytest.mark.parametrize("payload,content_type", INVALID_PAYLOADS)
def test_app_chat_conversation_put_invalid_json(client, auth_headers, payload, content_type):
    response = client.put("/api/chat/conversations/conv-123", headers=auth_headers, data=payload, content_type=content_type)
    assert response.status_code == 400
    assert "Invalid or missing JSON payload" in response.get_json()["error"]

@pytest.mark.parametrize("payload,content_type", INVALID_PAYLOADS)
def test_app_chat_conversation_messages_post_invalid_json(client, auth_headers, payload, content_type):
    response = client.post("/api/chat/conversations/conv-123/messages", headers=auth_headers, data=payload, content_type=content_type)
    assert response.status_code == 400
    assert "Invalid or missing JSON payload" in response.get_json()["error"]

@pytest.mark.parametrize("payload,content_type", INVALID_PAYLOADS)
def test_app_telegram_webhook_invalid_json(client, payload, content_type):
    response = client.post("/api/v1/telegram/webhook", data=payload, content_type=content_type)
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
