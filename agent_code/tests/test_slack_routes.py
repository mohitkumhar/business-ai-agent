import os
import json
import pytest
from unittest.mock import patch, MagicMock

from flask import Flask
from agent_code.slack_integration.flask_routes import register_slack_routes

# -----------------------

# Flask test fixture

# -----------------------

@pytest.fixture
def app():
app = Flask(**name**)
register_slack_routes(app)
app.config["TESTING"] = True
return app

@pytest.fixture
def client(app):
return app.test_client()

# -----------------------

# Helper

# -----------------------

def auth_headers():
return {
"X-Slack-Signature": "test-signature",
"X-Slack-Request-Timestamp": "1234567890",
}

# -----------------------

# Tests

# -----------------------

def test_slack_events_not_configured(client):
"""Slack not configured should return ok=True"""
with patch.dict(os.environ, {}, clear=True):
res = client.post(
"/slack/events",
data=json.dumps({"type": "event_callback"}),
headers=auth_headers(),
)
assert res.status_code == 200
assert res.json["ok"] is True

def test_slack_events_invalid_signature(client):
"""Invalid signature should return 403 when configured"""
with patch.dict(os.environ, {
"SLACK_BOT_TOKEN": "x",
"SLACK_SIGNING_SECRET": "y"
}):
with patch("slack_sdk.signature.SignatureVerifier.is_valid", return_value=False):
res = client.post(
"/slack/events",
data=json.dumps({"type": "event_callback"}),
headers=auth_headers(),
)
assert res.status_code == 403

def test_slack_url_verification(client):
"""Slack URL verification challenge"""
with patch.dict(os.environ, {
"SLACK_BOT_TOKEN": "x",
"SLACK_SIGNING_SECRET": "y"
}):
with patch("slack_sdk.signature.SignatureVerifier.is_valid", return_value=True):
res = client.post(
"/slack/events",
data=json.dumps({
"type": "url_verification",
"challenge": "abc123"
}),
headers=auth_headers(),
)
assert res.status_code == 200
assert res.json["challenge"] == "abc123"

def test_slack_interactive_invalid_payload(client):
"""Invalid interactive payload should return 400"""
with patch.dict(os.environ, {
"SLACK_BOT_TOKEN": "x",
"SLACK_SIGNING_SECRET": "y"
}):
with patch("slack_sdk.signature.SignatureVerifier.is_valid", return_value=True):
res = client.post(
"/slack/interactive",
data="payload=invalid-json",
headers=auth_headers(),
)
assert res.status_code == 400

def test_slack_interactive_no_action(client):
"""No valid action should return ok=True"""
with patch.dict(os.environ, {
"SLACK_BOT_TOKEN": "x",
"SLACK_SIGNING_SECRET": "y"
}):
with patch("slack_sdk.signature.SignatureVerifier.is_valid", return_value=True):
payload = {
"type": "block_actions",
"actions": []
}
res = client.post(
"/slack/interactive",
data=f"payload={json.dumps(payload)}",
headers=auth_headers(),
)
assert res.status_code == 200
assert res.json["ok"] is True
