from __future__ import annotations

import hashlib
import hmac
import json


def whatsapp_signature(body: bytes, secret: str = "test-whatsapp-secret") -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_whatsapp_verify_accepts_matching_token(client, app_module, monkeypatch):
    monkeypatch.setattr(app_module, "WHATSAPP_VERIFY_TOKEN", "verify-me")

    response = client.get(
        "/api/v1/whatsapp/webhook",
        query_string={"hub.verify_token": "verify-me", "hub.challenge": "abc123"},
    )

    assert response.status_code == 200
    assert response.data == b"abc123"


def test_whatsapp_verify_rejects_wrong_token(client, app_module, monkeypatch):
    monkeypatch.setattr(app_module, "WHATSAPP_VERIFY_TOKEN", "verify-me")

    response = client.get(
        "/api/v1/whatsapp/webhook",
        query_string={"hub.verify_token": "wrong", "hub.challenge": "abc123"},
    )

    assert response.status_code == 403


def test_whatsapp_webhook_rejects_missing_signature(client, app_module, monkeypatch):
    monkeypatch.setattr(app_module, "WHATSAPP_APP_SECRET", "test-whatsapp-secret")

    response = client.post("/api/v1/whatsapp/webhook", json={"entry": []})

    assert response.status_code == 403
    assert response.get_json()["error"] == "Invalid WhatsApp signature"


def test_whatsapp_webhook_rejects_invalid_signature(client, app_module, monkeypatch):
    monkeypatch.setattr(app_module, "WHATSAPP_APP_SECRET", "test-whatsapp-secret")

    response = client.post(
        "/api/v1/whatsapp/webhook",
        json={"entry": []},
        headers={"X-Hub-Signature-256": "sha256=bad"},
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == "Invalid WhatsApp signature"


def test_whatsapp_webhook_accepts_valid_signature(client, app_module, monkeypatch):
    monkeypatch.setattr(app_module, "WHATSAPP_APP_SECRET", "test-whatsapp-secret")
    body = json.dumps({"entry": []}, separators=(",", ":")).encode("utf-8")

    response = client.post(
        "/api/v1/whatsapp/webhook",
        data=body,
        content_type="application/json",
        headers={"X-Hub-Signature-256": whatsapp_signature(body)},
    )

    assert response.status_code == 200
    assert response.get_json() == {"ok": True}


def test_telegram_webhook_ignores_updates_without_chat(client, app_module, monkeypatch):
    monkeypatch.setattr(app_module, "TELEGRAM_WEBHOOK_SECRET", "telegram-secret")

    response = client.post(
        "/api/v1/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "telegram-secret"},
        json={"message": {"text": "hello"}},
    )

    assert response.status_code == 200
    assert response.get_json() == {"ok": True}


def test_telegram_webhook_rejects_missing_secret_token(client, app_module, monkeypatch):
    ran_agent = False
    sent_messages = []
    monkeypatch.setattr(app_module, "TELEGRAM_WEBHOOK_SECRET", "telegram-secret")

    def fake_run_agent(*args, **kwargs):
        nonlocal ran_agent
        ran_agent = True
        return "answer"

    monkeypatch.setattr(app_module, "_run_agent_to_text", fake_run_agent)
    monkeypatch.setattr(
        app_module,
        "_send_telegram_text",
        lambda chat_id, text: sent_messages.append((chat_id, text)),
    )

    response = client.post(
        "/api/v1/telegram/webhook",
        json={"message": {"chat": {"id": 42}, "text": "How are sales?"}},
    )

    assert response.status_code == 403
    assert response.get_json() == {"error": "Invalid Telegram webhook secret token"}
    assert ran_agent is False
    assert sent_messages == []


def test_telegram_webhook_rejects_wrong_secret_token(client, app_module, monkeypatch):
    ran_agent = False
    sent_messages = []
    monkeypatch.setattr(app_module, "TELEGRAM_WEBHOOK_SECRET", "telegram-secret")

    def fake_run_agent(*args, **kwargs):
        nonlocal ran_agent
        ran_agent = True
        return "answer"

    monkeypatch.setattr(app_module, "_run_agent_to_text", fake_run_agent)
    monkeypatch.setattr(
        app_module,
        "_send_telegram_text",
        lambda chat_id, text: sent_messages.append((chat_id, text)),
    )

    response = client.post(
        "/api/v1/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
        json={"message": {"chat": {"id": 42}, "text": "How are sales?"}},
    )

    assert response.status_code == 403
    assert response.get_json() == {"error": "Invalid Telegram webhook secret token"}
    assert ran_agent is False
    assert sent_messages == []


def test_telegram_webhook_replies_to_text_message(client, app_module, monkeypatch):
    sent_messages = []
    monkeypatch.setattr(app_module, "TELEGRAM_WEBHOOK_SECRET", "telegram-secret")
    monkeypatch.setattr(app_module, "DEFAULT_BUSINESS_ID", "business-1")
    monkeypatch.setattr(
        app_module, "_run_agent_to_text", lambda text, thread_id, bid: f"answer: {text}"
    )
    monkeypatch.setattr(
        app_module,
        "_send_telegram_text",
        lambda chat_id, text: sent_messages.append((chat_id, text)),
    )

    response = client.post(
        "/api/v1/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "telegram-secret"},
        json={"message": {"chat": {"id": 42}, "text": "How are sales?"}},
    )

    assert response.status_code == 200
    assert response.get_json() == {"ok": True}
    assert sent_messages == [(42, "answer: How are sales?")]
