from __future__ import annotations


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


def test_telegram_webhook_ignores_updates_without_chat(client):
    response = client.post("/api/v1/telegram/webhook", json={"message": {"text": "hello"}})

    assert response.status_code == 200
    assert response.get_json() == {"ok": True}


def test_telegram_webhook_replies_to_text_message(client, app_module, monkeypatch):
    sent_messages = []
    monkeypatch.setattr(app_module, "_run_agent_to_text", lambda text, thread_id, bid: f"answer: {text}")
    monkeypatch.setattr(app_module, "_send_telegram_text", lambda chat_id, text: sent_messages.append((chat_id, text)))

    response = client.post(
        "/api/v1/telegram/webhook",
        json={"message": {"chat": {"id": 42}, "text": "How are sales?"}},
    )

    assert response.status_code == 200
    assert response.get_json() == {"ok": True}
    assert sent_messages == [(42, "answer: How are sales?")]
