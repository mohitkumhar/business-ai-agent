from __future__ import annotations

import importlib.util
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import jwt
import pytest


AGENT_CODE_DIR = Path(__file__).resolve().parents[1]
if str(AGENT_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_CODE_DIR))


@pytest.fixture(scope="session")
def app_module(tmp_path_factory):
    os.environ.setdefault("GROQ_API_KEY", "test-key")
    os.environ.setdefault("OPENROUTER_API_KEY", "test-openrouter-key")
    os.environ.setdefault("JWT_SECRET", "test-secret")
    os.environ["USE_IN_MEMORY_CHECKPOINTER"] = "true"
    os.environ["CHAT_DB_PATH"] = str(tmp_path_factory.mktemp("chat") / "chat_history.sqlite")
    (AGENT_CODE_DIR / "logs").mkdir(exist_ok=True)
    module_path = AGENT_CODE_DIR / "app.py"
    spec = importlib.util.spec_from_file_location("profitpilot_agent_app", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
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
