import pytest
from agent_code.app_main import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_onboarding_missing_json(client):
    res = client.post("/api/v1/onboarding", content_type="application/json", data="bad json")
    assert res.status_code == 400

def test_chat_send_missing_json(client):
    res = client.post("/api/chat/send", content_type="application/json", data="bad json")
    assert res.status_code == 400