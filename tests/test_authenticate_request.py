from __future__ import annotations

from dataclasses import dataclass

from agent_code.nodes import authenticate_request


@dataclass
class FakeRequest:
    headers: dict
    json: dict | None = None


def test_authenticate_accepts_header_key(monkeypatch):
    monkeypatch.setattr(authenticate_request, "API_KEY", "expected")
    req = FakeRequest(headers={"X-API-KEY": "expected"}, json=None)

    ok, meta = authenticate_request.authenticate(req)

    assert ok is True
    assert meta["method_checked"] == "header/json"


def test_authenticate_accepts_json_key(monkeypatch):
    monkeypatch.setattr(authenticate_request, "API_KEY", "expected")
    req = FakeRequest(headers={}, json={"api_key": "expected"})

    ok, _ = authenticate_request.authenticate(req)

    assert ok is True


def test_authenticate_rejects_missing_or_wrong_key(monkeypatch):
    monkeypatch.setattr(authenticate_request, "API_KEY", "expected")
    req = FakeRequest(headers={"X-API-KEY": "wrong"}, json={"api_key": "wrong"})

    ok, meta = authenticate_request.authenticate(req)

    assert ok is False
    assert meta == {"error": "invalid_api_key"}


def test_authenticate_header_works_even_without_json_attribute(monkeypatch):
    monkeypatch.setattr(authenticate_request, "API_KEY", "expected")

    class HeaderOnlyRequest:
        headers = {"X-API-KEY": "expected"}

    ok, _ = authenticate_request.authenticate(HeaderOnlyRequest())

    assert ok is True
