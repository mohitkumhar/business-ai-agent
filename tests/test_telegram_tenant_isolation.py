"""Regression tests for Telegram webhook tenant isolation.

Verifies that the Telegram webhook in agent_code/app.py uses fail-closed
behaviour: when DEFAULT_BUSINESS_ID is empty or missing the webhook must
NOT invoke _run_agent_to_text, preventing cross-tenant data leakage.
"""
from __future__ import annotations

import os
import pytest


# A valid Telegram update payload with a text message.
TELEGRAM_TEXT_UPDATE = {
    "update_id": 123456,
    "message": {
        "message_id": 1,
        "from": {"id": 42, "is_bot": False, "first_name": "Test"},
        "chat": {"id": 42, "type": "private"},
        "date": 1700000000,
        "text": "What is my revenue?",
    },
}

# The old hardcoded seed UUID that must never be used as a fallback.
SEED_UUID = "550e8400-e29b-41d4-a716-446655440000"

# Shared secret used across all tests so the webhook secret gate passes.
TEST_WEBHOOK_SECRET = "test-telegram-webhook-secret"


# ---------------------------------------------------------------------------
# Core regression test: no business ID → _run_agent_to_text must NOT be called
# ---------------------------------------------------------------------------

def test_telegram_webhook_does_not_call_agent_when_no_business_id(
    agent_app_module, agent_client, monkeypatch
):
    """When DEFAULT_BUSINESS_ID is empty the webhook must refuse to run the
    agent, returning {"ok": true} without invoking _run_agent_to_text."""

    # Ensure DEFAULT_BUSINESS_ID is empty (unconfigured).
    monkeypatch.setattr(agent_app_module, "DEFAULT_BUSINESS_ID", "")
    monkeypatch.setattr(agent_app_module, "TELEGRAM_WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)

    agent_called = False

    def _spy_run_agent_to_text(query, thread_id, business_id):
        nonlocal agent_called
        agent_called = True
        return "mocked response"

    monkeypatch.setattr(agent_app_module, "_run_agent_to_text", _spy_run_agent_to_text)
    monkeypatch.setattr(agent_app_module, "_send_telegram_text", lambda *a, **kw: None)

    response = agent_client.post(
        "/api/v1/telegram/webhook",
        json=TELEGRAM_TEXT_UPDATE,
        headers={"X-Telegram-Bot-Api-Secret-Token": TEST_WEBHOOK_SECRET},
    )

    assert response.status_code == 200
    assert response.get_json().get("ok") is True
    assert not agent_called, (
        "_run_agent_to_text was called despite DEFAULT_BUSINESS_ID being empty. "
        "This is a cross-tenant data leakage risk."
    )


def test_telegram_webhook_no_hardcoded_uuid_fallback(
    agent_app_module, agent_client, monkeypatch
):
    """Ensure no hardcoded UUID fallback is used when DEFAULT_BUSINESS_ID is
    missing.  The agent must not be called with any business_id."""

    monkeypatch.setattr(agent_app_module, "DEFAULT_BUSINESS_ID", "")
    monkeypatch.setattr(agent_app_module, "TELEGRAM_WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)

    captured_business_ids: list[str] = []

    def _spy_run_agent_to_text(query, thread_id, business_id):
        captured_business_ids.append(business_id)
        return "mocked"

    monkeypatch.setattr(agent_app_module, "_run_agent_to_text", _spy_run_agent_to_text)
    monkeypatch.setattr(agent_app_module, "_send_telegram_text", lambda *a, **kw: None)

    agent_client.post(
        "/api/v1/telegram/webhook",
        json=TELEGRAM_TEXT_UPDATE,
        headers={"X-Telegram-Bot-Api-Secret-Token": TEST_WEBHOOK_SECRET},
    )

    assert captured_business_ids == [], (
        f"_run_agent_to_text was called with business_id(s) {captured_business_ids} "
        "when DEFAULT_BUSINESS_ID was empty."
    )


# ---------------------------------------------------------------------------
# Positive test: agent IS invoked when a valid business ID is configured
# ---------------------------------------------------------------------------

def test_telegram_webhook_calls_agent_when_business_id_configured(
    agent_app_module, agent_client, monkeypatch
):
    """When DEFAULT_BUSINESS_ID is properly set, the webhook should invoke
    _run_agent_to_text with that business ID."""

    test_biz_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    monkeypatch.setattr(agent_app_module, "DEFAULT_BUSINESS_ID", test_biz_id)
    monkeypatch.setattr(agent_app_module, "TELEGRAM_WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)

    captured: list[tuple[str, str, str]] = []

    def _spy_run_agent_to_text(query, thread_id, business_id):
        captured.append((query, thread_id, business_id))
        return "mocked response"

    monkeypatch.setattr(agent_app_module, "_run_agent_to_text", _spy_run_agent_to_text)
    monkeypatch.setattr(agent_app_module, "_send_telegram_text", lambda *a, **kw: None)

    response = agent_client.post(
        "/api/v1/telegram/webhook",
        json=TELEGRAM_TEXT_UPDATE,
        headers={"X-Telegram-Bot-Api-Secret-Token": TEST_WEBHOOK_SECRET},
    )

    assert response.status_code == 200
    assert len(captured) == 1, "_run_agent_to_text should be called exactly once"
    assert captured[0][2] == test_biz_id, (
        f"Expected business_id={test_biz_id!r} but got {captured[0][2]!r}"
    )


# ---------------------------------------------------------------------------
# Edge-case: ensure the seed UUID from the old code is never used
# ---------------------------------------------------------------------------

def test_telegram_webhook_never_uses_seed_uuid(
    agent_app_module, agent_client, monkeypatch
):
    """The old hardcoded seed UUID must never appear as a business_id passed
    to _run_agent_to_text, regardless of DEFAULT_BUSINESS_ID value."""

    monkeypatch.setattr(agent_app_module, "DEFAULT_BUSINESS_ID", "")
    monkeypatch.setattr(agent_app_module, "TELEGRAM_WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)

    captured_business_ids: list[str] = []

    def _spy_run_agent_to_text(query, thread_id, business_id):
        captured_business_ids.append(business_id)
        return "mocked"

    monkeypatch.setattr(agent_app_module, "_run_agent_to_text", _spy_run_agent_to_text)
    monkeypatch.setattr(agent_app_module, "_send_telegram_text", lambda *a, **kw: None)

    agent_client.post(
        "/api/v1/telegram/webhook",
        json=TELEGRAM_TEXT_UPDATE,
        headers={"X-Telegram-Bot-Api-Secret-Token": TEST_WEBHOOK_SECRET},
    )

    assert SEED_UUID not in captured_business_ids, (
        f"The hardcoded seed UUID {SEED_UUID} was used as a business_id fallback. "
        "This is the exact cross-tenant leakage bug that was previously fixed."
    )
