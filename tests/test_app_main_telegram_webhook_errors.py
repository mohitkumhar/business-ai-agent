from __future__ import annotations

import ast
import importlib.util
import json
import sys
import types
from pathlib import Path


APP_MAIN = Path(__file__).resolve().parents[1] / "agent_code" / "app_main.py"
AGENT_CODE = APP_MAIN.parent


def _function_named(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} was not found")


def _exception_name(node: ast.expr | None) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Tuple):
        return ",".join(_exception_name(elt) for elt in node.elts)
    return ""


def test_app_main_telegram_webhook_does_not_use_catch_all_handler():
    tree = ast.parse(APP_MAIN.read_text())
    route = _function_named(tree, "telegram_webhook")

    caught_names = {
        _exception_name(handler.type)
        for handler in ast.walk(route)
        if isinstance(handler, ast.ExceptHandler)
    }

    assert "Exception" not in caught_names
    assert "BaseException" not in caught_names
    assert "TELEGRAM_WEBHOOK_EXPECTED_ERRORS" in caught_names


def test_app_main_telegram_webhook_emits_structured_failure_context():
    source = APP_MAIN.read_text()

    assert "WEBHOOK_FAILURE_COUNT.labels(\"telegram\", stage, exception_type).inc()" in source
    assert "json.dumps(" in source
    assert "\"error_code\": TELEGRAM_WEBHOOK_ERROR_CODE" in source
    assert "\"stage\": stage" in source
    assert "\"error_type\": type(exc).__name__" in source


def test_app_main_telegram_send_does_not_silently_skip_operational_failures():
    tree = ast.parse(APP_MAIN.read_text())
    helper = _function_named(tree, "_send_telegram_text")

    assert not any(isinstance(node, ast.ExceptHandler) for node in ast.walk(helper))
    assert 'raise ValueError("TELEGRAM_BOT_TOKEN is not configured.")' in APP_MAIN.read_text()


def test_app_main_telegram_webhook_runtime_failure_contract(monkeypatch):
    module = _load_app_main_first_section(monkeypatch)
    module.app.config.update(TESTING=True)
    client = module.app.test_client()

    original_send = module._send_telegram_text
    sent_messages = []
    monkeypatch.setattr(
        module,
        "_send_telegram_text",
        lambda chat_id, text: sent_messages.append((chat_id, text)),
    )
    monkeypatch.setattr(
        module,
        "_run_agent_to_text",
        lambda text, thread_id, business_id: f"answer:{text}:{thread_id}:{business_id}",
    )
    monkeypatch.setattr(module, "DEFAULT_BUSINESS_ID", "business-1")

    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "update_id": 1,
            "message": {"message_id": 2, "chat": {"id": 42}, "text": "hello"},
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {"ok": True}
    assert sent_messages == [(42, "answer:hello:tg-42:business-1")]

    monkeypatch.setattr(
        module,
        "_run_agent_to_text",
        _raises(RuntimeError("agent exploded with secret")),
    )
    response = client.post(
        "/api/v1/telegram/webhook",
        json={"update_id": 3, "message": {"chat": {"id": 99}, "text": "break"}},
    )

    assert response.status_code == 500
    assert response.get_json() == {
        "ok": False,
        "error": module.SAFE_INTERNAL_ERROR_MESSAGE,
        "error_code": module.TELEGRAM_WEBHOOK_ERROR_CODE,
        "stage": "run_agent",
        "error_type": "RuntimeError",
    }
    assert "secret" not in response.get_data(as_text=True)

    response = client.post(
        "/api/v1/telegram/webhook",
        data="{bad",
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.get_json()["stage"] == "parse_update"
    assert response.get_json()["error_type"] == "BadRequest"

    response = client.post("/api/v1/telegram/webhook", json=[])

    assert response.status_code == 400
    assert response.get_json()["stage"] == "parse_update"
    assert response.get_json()["error_type"] == "ValueError"

    response = client.post("/api/v1/telegram/webhook", json={"message": []})

    assert response.status_code == 400
    assert response.get_json()["stage"] == "extract_message"
    assert response.get_json()["error_type"] == "ValueError"

    response = client.post("/api/v1/telegram/webhook", json={"message": None})

    assert response.status_code == 400
    assert response.get_json()["stage"] == "extract_message"
    assert response.get_json()["error_type"] == "ValueError"

    response = client.post(
        "/api/v1/telegram/webhook",
        json={"message": {"chat": [], "text": "hello"}},
    )

    assert response.status_code == 400
    assert response.get_json()["stage"] == "extract_chat"
    assert response.get_json()["error_type"] == "ValueError"

    response = client.post(
        "/api/v1/telegram/webhook",
        json={"message": {"chat": None, "text": "hello"}},
    )

    assert response.status_code == 400
    assert response.get_json()["stage"] == "extract_chat"
    assert response.get_json()["error_type"] == "ValueError"

    response = client.post(
        "/api/v1/telegram/webhook",
        json={"message": {"chat": {"id": True}, "text": "hello"}},
    )

    assert response.status_code == 400
    assert response.get_json()["stage"] == "extract_chat"
    assert response.get_json()["error_type"] == "ValueError"

    response = client.post(
        "/api/v1/telegram/webhook",
        json={"message": {"chat": {"id": 7}, "photo": ""}},
    )

    assert response.status_code == 400
    assert response.get_json()["stage"] == "parse_content"
    assert response.get_json()["error_type"] == "ValueError"

    response = client.post(
        "/api/v1/telegram/webhook",
        json={"message": {"chat": {"id": 7}, "photo": None}},
    )

    assert response.status_code == 400
    assert response.get_json()["stage"] == "parse_content"
    assert response.get_json()["error_type"] == "ValueError"

    response = client.post(
        "/api/v1/telegram/webhook",
        json={"message": {"chat": {"id": 7}, "text": ["not", "a", "string"]}},
    )

    assert response.status_code == 400
    assert response.get_json()["stage"] == "parse_content"
    assert response.get_json()["error_type"] == "ValueError"

    response = client.post(
        "/api/v1/telegram/webhook",
        json={"message": {"chat": {"id": 7}, "caption": None}},
    )

    assert response.status_code == 400
    assert response.get_json()["stage"] == "parse_content"
    assert response.get_json()["error_type"] == "ValueError"

    response = client.post(
        "/api/v1/telegram/webhook",
        json={"message": {"chat": {"id": 7}, "photo": [{"file_size": 12}]}},
    )

    assert response.status_code == 400
    assert response.get_json()["stage"] == "select_photo"
    assert response.get_json()["error_type"] == "ValueError"

    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "chat": {"id": 7},
                "photo": [{"file_id": "file-1", "file_size": "large"}],
            }
        },
    )

    assert response.status_code == 400
    assert response.get_json()["stage"] == "select_photo"
    assert response.get_json()["error_type"] == "ValueError"

    monkeypatch.setattr(module, "_run_agent_to_text", lambda *args, **kwargs: "ok")
    monkeypatch.setattr(module, "_send_telegram_text", original_send)
    monkeypatch.setattr(module, "TELEGRAM_BOT_TOKEN", "")
    response = client.post(
        "/api/v1/telegram/webhook",
        json={"message": {"chat": {"id": 7}, "text": "send"}},
    )

    assert response.status_code == 500
    assert response.get_json()["stage"] == "send_reply"
    assert response.get_json()["error_type"] == "ValueError"

    monkeypatch.setattr(module, "TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setattr(module.requests, "post", _raises(module.requests.Timeout("network down")))
    response = client.post(
        "/api/v1/telegram/webhook",
        json={"message": {"chat": {"id": 8}, "text": "send"}},
    )

    assert response.status_code == 500
    assert response.get_json()["stage"] == "send_reply"
    assert response.get_json()["error_type"] == "Timeout"

    metrics = module.generate_latest(module.REGISTRY).decode()
    assert 'platform="telegram",stage="run_agent",exception_type="RuntimeError"' in metrics
    assert 'platform="telegram",stage="parse_update",exception_type="BadRequest"' in metrics
    assert 'platform="telegram",stage="parse_update",exception_type="ValueError"' in metrics
    assert 'platform="telegram",stage="extract_message",exception_type="ValueError"' in metrics
    assert 'platform="telegram",stage="extract_chat",exception_type="ValueError"' in metrics
    assert 'platform="telegram",stage="parse_content",exception_type="ValueError"' in metrics
    assert 'platform="telegram",stage="select_photo",exception_type="ValueError"' in metrics
    assert 'platform="telegram",stage="send_reply",exception_type="ValueError"' in metrics
    assert 'platform="telegram",stage="send_reply",exception_type="Timeout"' in metrics


def _raises(exc: BaseException):
    def _raise(*args, **kwargs):
        raise exc

    return _raise


def _load_app_main_first_section(monkeypatch):
    monkeypatch.syspath_prepend(str(AGENT_CODE))
    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    monkeypatch.setenv("OPENROUTER_API_KEY", "ci-placeholder")
    monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

    if importlib.util.find_spec("flask") is None:
        bad_request = type("BadRequest", (Exception,), {})
        monkeypatch.setitem(sys.modules, "werkzeug", types.ModuleType("werkzeug"))
        monkeypatch.setitem(
            sys.modules,
            "werkzeug.exceptions",
            _fake_werkzeug_exceptions(bad_request),
        )
        monkeypatch.setitem(sys.modules, "flask", _fake_flask_module(bad_request))
        monkeypatch.setitem(sys.modules, "flask_cors", _fake_flask_cors_module())
    elif importlib.util.find_spec("flask_cors") is None:
        monkeypatch.setitem(sys.modules, "flask_cors", _fake_flask_cors_module())

    monkeypatch.setitem(sys.modules, "dotenv", _fake_dotenv_module())
    if importlib.util.find_spec("requests") is None:
        monkeypatch.setitem(sys.modules, "requests", _fake_requests_module())
    monkeypatch.setitem(sys.modules, "prometheus_client", _fake_prometheus_module())
    if importlib.util.find_spec("jwt") is None:
        monkeypatch.setitem(sys.modules, "auth", _fake_auth_module())
    if importlib.util.find_spec("bcrypt") is None:
        monkeypatch.setitem(sys.modules, "auth_passwords", _fake_auth_passwords_module())
    _install_fake_langchain_messages(monkeypatch)

    base_llm_module = types.ModuleType("llm.base_llm")
    base_llm_module.base_llm = types.SimpleNamespace(
        invoke=lambda *args, **kwargs: types.SimpleNamespace(content="{}")
    )
    monkeypatch.setitem(sys.modules, "llm.base_llm", base_llm_module)

    query_execution = types.ModuleType("query_execution")
    query_execution.stream_agent_sse_lines = lambda *args, **kwargs: iter(())
    monkeypatch.setitem(sys.modules, "query_execution", query_execution)
    monkeypatch.setitem(sys.modules, "db_config", _fake_db_config_module())

    source = APP_MAIN.read_text()
    first_section = source.split('\nif __name__ == "__main__":', 1)[0]
    module = types.ModuleType("app_main_first_section_runtime")
    module.__file__ = str(APP_MAIN)
    exec(compile(first_section, module.__file__, "exec"), module.__dict__)
    return module


def _fake_dotenv_module():
    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda *args, **kwargs: None
    return dotenv


def _fake_werkzeug_exceptions(bad_request):
    exceptions = types.ModuleType("werkzeug.exceptions")
    exceptions.BadRequest = bad_request
    return exceptions


def _fake_flask_cors_module():
    flask_cors = types.ModuleType("flask_cors")
    flask_cors.CORS = lambda *args, **kwargs: None
    return flask_cors


def _fake_flask_module(bad_request):
    flask = types.ModuleType("flask")
    request = _RequestProxy(bad_request)
    g = types.SimpleNamespace()

    class Flask:
        def __init__(self, name):
            self.name = name
            self.config = {}
            self._before_request = []
            self._after_request = []
            self._routes = {}

        def before_request(self, func):
            self._before_request.append(func)
            return func

        def after_request(self, func):
            self._after_request.append(func)
            return func

        def route(self, path, methods=None):
            route_methods = tuple(methods or ("GET",))

            def _decorator(func):
                for method in route_methods:
                    self._routes[(path, method.upper())] = func
                return func

            return _decorator

        def test_client(self):
            return _TestClient(self, request, g)

        def run(self, *args, **kwargs):
            return None

    flask.Flask = Flask
    flask.Response = _Response
    flask.jsonify = lambda payload=None, **kwargs: _Response(payload if payload is not None else kwargs)
    flask.request = request
    flask.g = g
    flask.stream_with_context = lambda generator: generator
    return flask


class _RequestProxy:
    _missing = object()

    def __init__(self, bad_request):
        self._bad_request = bad_request
        self.reset()

    def reset(self):
        self.path = ""
        self.endpoint = ""
        self.method = ""
        self.headers = {}
        self.args = {}
        self.json = None
        self._json_payload = self._missing
        self._data = None

    def get_json(self, force=False):
        if self._json_payload is not self._missing:
            return self._json_payload
        if self._data is None:
            return None
        try:
            return json.loads(self._data)
        except json.JSONDecodeError as exc:
            raise self._bad_request("Invalid JSON payload") from exc


class _Response:
    def __init__(self, payload=None, status_code=200, mimetype=None):
        self.payload = payload
        self.status_code = status_code
        self.mimetype = mimetype
        self.headers = {}

    def get_json(self):
        return self.payload

    def get_data(self, as_text=False):
        if isinstance(self.payload, (dict, list)):
            data = json.dumps(self.payload)
        elif self.payload is None:
            data = ""
        elif isinstance(self.payload, bytes):
            return self.payload.decode() if as_text else self.payload
        else:
            data = str(self.payload)
        return data if as_text else data.encode()

    @property
    def data(self):
        return self.get_data()


class _TestClient:
    def __init__(self, app, request, g):
        self.app = app
        self.request = request
        self.g = g

    def post(self, path, json=_RequestProxy._missing, data=None, content_type=None):
        return self._open("POST", path, json_payload=json, data=data, content_type=content_type)

    def _open(self, method, path, json_payload=_RequestProxy._missing, data=None, content_type=None):
        handler = self.app._routes[(path, method)]
        self.request.reset()
        self.g.__dict__.clear()
        self.request.path = path
        self.request.endpoint = handler.__name__
        self.request.method = method
        self.request._json_payload = json_payload
        self.request.json = None if json_payload is _RequestProxy._missing else json_payload
        self.request._data = data
        self.request.content_type = content_type

        for before in self.app._before_request:
            before()
        response = self._normalize_response(handler())
        for after in self.app._after_request:
            response = after(response)
        return response

    @staticmethod
    def _normalize_response(value):
        if isinstance(value, tuple):
            response, status_code = value
            response = response if isinstance(response, _Response) else _Response(response)
            response.status_code = status_code
            return response
        if isinstance(value, _Response):
            return value
        return _Response(value)


def _fake_requests_module():
    requests = types.ModuleType("requests")

    class RequestException(Exception):
        pass

    class Timeout(RequestException):
        pass

    def _unexpected_request(*args, **kwargs):
        raise AssertionError("Unexpected HTTP request in Telegram webhook test")

    requests.RequestException = RequestException
    requests.Timeout = Timeout
    requests.get = _unexpected_request
    requests.post = _unexpected_request
    return requests


def _fake_auth_module():
    auth = types.ModuleType("auth")

    class AuthError(Exception):
        def __init__(self, message, status_code=401):
            super().__init__(message)
            self.message = message
            self.status_code = status_code

    auth.AuthError = AuthError
    auth.decode_jwt_identity = lambda *args, **kwargs: {"user_id": "u", "business_id": "b"}
    auth.require_jwt_secret = lambda raw_secret: raw_secret or "test-secret"
    return auth


def _fake_auth_passwords_module():
    auth_passwords = types.ModuleType("auth_passwords")
    auth_passwords.SOCIAL_LOGIN_PASSWORD_HASH = "test-password-hash"
    return auth_passwords


def _install_fake_langchain_messages(monkeypatch):
    messages = types.ModuleType("langchain_core.messages")

    class HumanMessage:
        def __init__(self, content=None):
            self.content = content

    class SystemMessage:
        def __init__(self, content=None):
            self.content = content

    messages.HumanMessage = HumanMessage
    messages.SystemMessage = SystemMessage
    langchain_core = types.ModuleType("langchain_core")
    langchain_core.messages = messages
    monkeypatch.setitem(sys.modules, "langchain_core", langchain_core)
    monkeypatch.setitem(sys.modules, "langchain_core.messages", messages)


def _fake_prometheus_module():
    prometheus = types.ModuleType("prometheus_client")
    registry = object()
    metrics: dict[str, dict[tuple[str, ...], float]] = {}

    class _Metric:
        def __init__(self, name, description, labelnames=None, **kwargs):
            self.name = name
            self.labelnames = tuple(labelnames or ())
            metrics.setdefault(name, {})

        def labels(self, *values):
            self.values = tuple(str(value) for value in values)
            return self

        def inc(self, amount=1):
            metrics[self.name][self.values] = metrics[self.name].get(self.values, 0) + amount

        def observe(self, value):
            return None

    def generate_latest(_registry):
        lines = []
        for name, samples in metrics.items():
            for values, amount in samples.items():
                labels = ",".join(
                    f'{label}="{value}"'
                    for label, value in zip(("platform", "stage", "exception_type"), values)
                )
                lines.append(f"{name}{{{labels}}} {float(amount)}")
        return "\n".join(lines).encode()

    prometheus.Counter = _Metric
    prometheus.Histogram = _Metric
    prometheus.REGISTRY = registry
    prometheus.CONTENT_TYPE_LATEST = "text/plain"
    prometheus.generate_latest = generate_latest
    return prometheus


def _fake_db_config_module():
    db_config = types.ModuleType("db_config")

    class _Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, *args, **kwargs):
            return None

        def fetchone(self):
            return [101]

        def close(self):
            return None

    class _Connection:
        def cursor(self, *args, **kwargs):
            return _Cursor()

        def commit(self):
            return None

        def close(self):
            return None

    def execute_read_query_params(sql, params=None):
        if "FROM public.businesses" in sql:
            return [{"business_id": "business-1"}]
        return []

    db_config.get_db_connection = lambda: _Connection()
    db_config.execute_read_query_params = execute_read_query_params
    return db_config
