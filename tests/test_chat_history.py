from __future__ import annotations

import importlib.util
import os
import sys
import types
from datetime import datetime, timedelta
from pathlib import Path

import jwt
import pytest


AGENT_CODE_DIR = Path(__file__).resolve().parents[1] / "agent_code"
if str(AGENT_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_CODE_DIR))


class _NoopWorkflow:
    def stream(self, *args, **kwargs):
        return iter(())


def _install_chat_history_import_stubs() -> None:
    if "numpy" not in sys.modules and importlib.util.find_spec("numpy") is None:
        numpy = types.ModuleType("numpy")
        numpy.__chat_history_stub__ = True
        sys.modules["numpy"] = numpy

    if "langchain_openai" not in sys.modules and importlib.util.find_spec("langchain_openai") is None:
        langchain_openai = types.ModuleType("langchain_openai")

        class ChatOpenAI:
            def __init__(self, *args, **kwargs):
                pass

        langchain_openai.ChatOpenAI = ChatOpenAI
        sys.modules["langchain_openai"] = langchain_openai

    if "langgraph" not in sys.modules and importlib.util.find_spec("langgraph") is None:
        langgraph = types.ModuleType("langgraph")
        langgraph_types = types.ModuleType("langgraph.types")

        class Command(dict):
            pass

        langgraph_types.Command = Command
        sys.modules["langgraph"] = langgraph
        sys.modules["langgraph.types"] = langgraph_types

    workflow_modules = {
        "intents.general_information_graph.subgraph": "general_information_graph_workflow",
        "intents.database_request_graph.subgraph": "database_request_graph_workflow",
        "intents.logs_request_graph.subgraph": "logs_request_graph_workflow",
        "intents.metrics_request_graph.subgraph": "metrics_request_graph_workflow",
    }
    for module_name, workflow_name in workflow_modules.items():
        if module_name not in sys.modules:
            module = types.ModuleType(module_name)
            setattr(module, workflow_name, _NoopWorkflow())
            sys.modules[module_name] = module


def _remove_import_stub(module_name: str) -> None:
    module = sys.modules.get(module_name)
    if getattr(module, "__chat_history_stub__", False):
        sys.modules.pop(module_name, None)


@pytest.fixture(scope="session")
def app_module(tmp_path_factory):
    os.environ.setdefault("GROQ_API_KEY", "test-key")
    os.environ.setdefault("OPENROUTER_API_KEY", "test-openrouter-key")
    os.environ.setdefault("JWT_SECRET", "test-secret")
    os.environ["USE_IN_MEMORY_CHECKPOINTER"] = "true"
    os.environ["CHAT_DB_PATH"] = str(tmp_path_factory.mktemp("chat") / "chat_history.sqlite")
    (AGENT_CODE_DIR / "logs").mkdir(exist_ok=True)
    _install_chat_history_import_stubs()
    module_path = AGENT_CODE_DIR / "app.py"
    spec = importlib.util.spec_from_file_location("profitpilot_agent_app", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    finally:
        _remove_import_stub("numpy")
    module.app.config.update(TESTING=True, RATELIMIT_ENABLED=False, SECRET_KEY="test-secret")
    return module


@pytest.fixture()
def client(app_module):
    return app_module.app.test_client()


@pytest.fixture()
def auth_headers(app_module):
    token = jwt.encode(
        {
            "user_id": "user-1",
            "business_id": "business-1",
            "exp": datetime.utcnow() + timedelta(hours=1),
        },
        app_module.app.config["SECRET_KEY"],
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def _make_auth_headers(app_module, *, user_id: str, business_id: str) -> dict[str, str]:
    token = jwt.encode(
        {
            "user_id": user_id,
            "business_id": business_id,
            "exp": datetime.utcnow() + timedelta(hours=1),
        },
        app_module.app.config["SECRET_KEY"],
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def test_chat_conversations_require_authentication(client):
    response = client.get("/api/chat/conversations")

    assert response.status_code == 401
    assert response.get_json()["message"] == "Authorization header is required"


def test_chat_conversation_messages_round_trip(client, auth_headers):
    response = client.post(
        "/api/chat/conversations/conv-1/messages",
        headers=auth_headers,
        json={
            "title": "Revenue review",
            "message": {
                "role": "user",
                "content": "What was revenue last month?",
                "timestamp": 1710000000000,
            },
        },
    )

    assert response.status_code == 201

    response = client.post(
        "/api/chat/conversations/conv-1/messages",
        headers=auth_headers,
        json={
            "title": "Revenue review",
            "message": {
                "role": "assistant",
                "content": "Revenue was up 12%.",
                "intent": "metrics_request",
                "timestamp": 1710000000100,
            },
        },
    )

    assert response.status_code == 201

    response = client.get("/api/chat/conversations", headers=auth_headers)

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["conversations"] == [
        {
            "id": "conv-1",
            "title": "Revenue review",
            "createdAt": 1710000000000,
            "updatedAt": 1710000000100,
            "messages": [
                {
                    "role": "user",
                    "content": "What was revenue last month?",
                    "intent": None,
                    "timestamp": 1710000000000,
                },
                {
                    "role": "assistant",
                    "content": "Revenue was up 12%.",
                    "intent": "metrics_request",
                    "timestamp": 1710000000100,
                },
            ],
        }
    ]


def test_chat_conversations_are_scoped_to_authenticated_owner(client, app_module, auth_headers):
    response = client.post(
        "/api/chat/conversations/conv-1/messages",
        headers=auth_headers,
        json={
            "title": "Private chat",
            "message": {
                "role": "user",
                "content": "Show my private numbers",
                "timestamp": 1710000000000,
            },
        },
    )

    assert response.status_code == 201

    other_headers = _make_auth_headers(
        app_module,
        user_id="user-2",
        business_id="business-2",
    )

    response = client.get("/api/chat/conversations", headers=other_headers)

    assert response.status_code == 200
    assert response.get_json() == {"conversations": []}


def test_put_chat_conversation_dedupes_existing_messages(client, auth_headers):
    payload = {
        "title": "Imported chat",
        "createdAt": 1710000000000,
        "updatedAt": 1710000000300,
        "messages": [
            {
                "role": "user",
                "content": "What changed this week?",
                "timestamp": 1710000000000,
            },
            {
                "role": "assistant",
                "content": "Revenue improved while expenses stayed flat.",
                "intent": "database_request",
                "timestamp": 1710000000300,
            },
        ],
    }

    response = client.put(
        "/api/chat/conversations/import-1",
        headers=auth_headers,
        json=payload,
    )

    assert response.status_code == 200

    response = client.put(
        "/api/chat/conversations/import-1",
        headers=auth_headers,
        json=payload,
    )

    assert response.status_code == 200

    response = client.get("/api/chat/conversations/import-1", headers=auth_headers)

    conversation = response.get_json()["conversation"]
    assert response.status_code == 200
    assert conversation["messages"] == [
        {
            "role": "user",
            "content": "What changed this week?",
            "intent": None,
            "timestamp": 1710000000000,
        },
        {
            "role": "assistant",
            "content": "Revenue improved while expenses stayed flat.",
            "intent": "database_request",
            "timestamp": 1710000000300,
        },
    ]
    assert conversation["updatedAt"] == 1710000000300


def test_delete_chat_conversation_removes_it_from_history(client, auth_headers):
    response = client.put(
        "/api/chat/conversations/conv-delete",
        headers=auth_headers,
        json={
            "title": "Delete me",
            "createdAt": 1710000000000,
            "updatedAt": 1710000000000,
            "messages": [
                {
                    "role": "user",
                    "content": "Ephemeral note",
                    "timestamp": 1710000000000,
                }
            ],
        },
    )

    assert response.status_code == 200

    response = client.delete("/api/chat/conversations/conv-delete", headers=auth_headers)

    assert response.status_code == 204

    response = client.get("/api/chat/conversations", headers=auth_headers)

    payload = response.get_json()
    assert response.status_code == 200
    assert all(conversation["id"] != "conv-delete" for conversation in payload["conversations"])
