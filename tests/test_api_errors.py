from __future__ import annotations

import importlib
import json
import re
import sys
import types
from pathlib import Path


def test_internal_error_response_hides_raw_exception_message():
    api_errors = _load_api_errors_with_fake_flask()

    response, status = api_errors.internal_error_response(
        RuntimeError("password=secret db host internal.example")
    )

    assert status == 500
    assert response.get_json() == {"error": api_errors.SAFE_INTERNAL_ERROR_MESSAGE}
    assert response.headers["X-Request-ID"] == "req-123"
    assert "secret" not in response.get_data(as_text=True)
    assert "internal.example" not in response.get_data(as_text=True)


def test_internal_error_response_supports_message_field_for_auth_routes():
    api_errors = _load_api_errors_with_fake_flask()

    response, status = api_errors.internal_error_response(
        RuntimeError("duplicate key"), field="message"
    )

    assert status == 500
    assert response.get_json() == {"message": api_errors.SAFE_INTERNAL_ERROR_MESSAGE}
    assert response.headers["X-Request-ID"] == "req-123"


def test_internal_error_response_rejects_invalid_request_ids():
    api_errors = _load_api_errors_with_fake_flask(request_id="bad\r\nrequest-id")

    response, status = api_errors.internal_error_response(RuntimeError("duplicate key"))

    assert status == 500
    assert response.get_json() == {"error": api_errors.SAFE_INTERNAL_ERROR_MESSAGE}
    assert re.fullmatch(r"[0-9a-f]{32}", response.headers["X-Request-ID"])
    assert response.headers["X-Request-ID"] != "bad\r\nrequest-id"


def test_api_routes_do_not_return_raw_exception_strings_for_500s():
    root = Path(__file__).resolve().parents[1]
    for relative_path in ("agent_code/app.py", "agent_code/app_main.py", "web/app.py"):
        source = (root / relative_path).read_text(encoding="utf-8")
        assert 'jsonify({"error": str(' not in source
        assert 'jsonify({"message": str(' not in source


def _load_api_errors_with_fake_flask(request_id="req-123"):
    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload
            self.headers = {}

        def get_json(self):
            return self._payload

        def get_data(self, as_text=False):
            data = json.dumps(self._payload)
            return data if as_text else data.encode()

    previous_flask = sys.modules.get("flask")
    fake_flask = types.ModuleType("flask")
    fake_flask.g = types.SimpleNamespace(request_id=request_id)
    fake_flask.jsonify = lambda payload: FakeResponse(payload)
    sys.modules["flask"] = fake_flask
    sys.modules.pop("agent_code.api_errors", None)
    try:
        return importlib.import_module("agent_code.api_errors")
    finally:
        if previous_flask is None:
            sys.modules.pop("flask", None)
        else:
            sys.modules["flask"] = previous_flask
