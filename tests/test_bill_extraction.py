from __future__ import annotations

from datetime import date

import importlib

import pytest


@pytest.fixture()
def app_module(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "unit-test-jwt-secret")
    monkeypatch.setenv("OPENROUTER_API_KEY", "unit-test-openrouter-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

    try:
        module = importlib.import_module("agent_code.app")
    except Exception as exc:
        pytest.skip(f"backend app dependencies unavailable: {exc}")

    module.app.config.update(TESTING=True, RATELIMIT_ENABLED=False)
    return module


def test_extract_bill_data_rejects_zero_amount(app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "extract_transactions_from_image",
        lambda image_bytes, filename: [
            (date(2026, 5, 20), "Expense", "Inventory", 0, "Supplier bill")
        ],
    )

    with pytest.raises(ValueError, match="amount must be greater than zero"):
        app_module._extract_bill_data_from_image(b"image-bytes", "image/png")


def test_extract_bill_data_rejects_invalid_transaction_shape(app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "extract_transactions_from_image",
        lambda image_bytes, filename: [("not-a-transaction",)],
    )

    with pytest.raises(ValueError, match="invalid transaction shape"):
        app_module._extract_bill_data_from_image(b"image-bytes", "image/jpeg")


def test_extract_bill_data_rejects_invalid_date(app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "extract_transactions_from_image",
        lambda image_bytes, filename: [
            ("tomorrow-ish", "Expense", "Inventory", 45, "Supplier bill")
        ],
    )

    with pytest.raises(ValueError, match="invalid transaction date"):
        app_module._extract_bill_data_from_image(b"image-bytes", "image/jpeg")


def test_extract_bill_data_normalizes_valid_transaction(app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "extract_transactions_from_image",
        lambda image_bytes, filename: [
            ("2026-05-20", "expense", " Inventory ", "1450.75", " Supplier bill ")
        ],
    )

    payload = app_module._extract_bill_data_from_image(b"image-bytes", "image/webp")

    assert payload == {
        "date": date(2026, 5, 20),
        "amount": 1450.75,
        "category": "Inventory",
        "type": "Expense",
        "vendor": "Supplier bill",
    }
