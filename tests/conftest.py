from __future__ import annotations

import os
import sys
import types
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENT_CODE = ROOT / "agent_code"

for path in (ROOT, AGENT_CODE):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

os.environ.setdefault("OPENROUTER_API_KEY", "unit-test-openrouter-key")
os.environ.setdefault("OPENROUTER_MODEL", "openai/gpt-4o-mini")


if importlib.util.find_spec("dotenv") is None:
    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda *args, **kwargs: None
    sys.modules["dotenv"] = dotenv


if importlib.util.find_spec("psycopg2") is None:
    psycopg2 = types.ModuleType("psycopg2")
    extras = types.ModuleType("psycopg2.extras")

    class RealDictCursor:
        pass

    def _missing_connect(*args, **kwargs):
        raise RuntimeError("psycopg2 is not installed in the unit-test environment")

    extras.RealDictCursor = RealDictCursor
    psycopg2.extras = extras
    psycopg2.connect = _missing_connect
    sys.modules["psycopg2"] = psycopg2
    sys.modules["psycopg2.extras"] = extras


if importlib.util.find_spec("pydantic") is None:
    pydantic = types.ModuleType("pydantic")

    class BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        def model_dump(self):
            return dict(self.__dict__)

    def Field(*args, **kwargs):
        return kwargs.get("default")

    pydantic.BaseModel = BaseModel
    pydantic.Field = Field
    sys.modules["pydantic"] = pydantic


if importlib.util.find_spec("langchain_core") is None:
    langchain_core = types.ModuleType("langchain_core")
    prompts = types.ModuleType("langchain_core.prompts")
    runnables = types.ModuleType("langchain_core.runnables")

    class _Prompt:
        def __init__(self, messages):
            self._messages = messages

        def to_messages(self):
            return self._messages

    class ChatPromptTemplate:
        def __init__(self, messages):
            self._messages = messages

        @classmethod
        def from_messages(cls, messages):
            return cls(messages)

        def format_prompt(self, **kwargs):
            return _Prompt(self._messages)

    class RunnableConfig:
        pass

    prompts.ChatPromptTemplate = ChatPromptTemplate
    runnables.RunnableConfig = RunnableConfig
    langchain_core.prompts = prompts
    langchain_core.runnables = runnables
    sys.modules["langchain_core"] = langchain_core
    sys.modules["langchain_core.prompts"] = prompts
    sys.modules["langchain_core.runnables"] = runnables


if "llm.base_llm" not in sys.modules and importlib.util.find_spec("langchain_openai") is None:
    base_llm_module = types.ModuleType("llm.base_llm")

    class _FakeLLM:
        def with_structured_output(self, *args, **kwargs):
            return self

        def invoke(self, *args, **kwargs):
            return types.SimpleNamespace(content="", model_dump=lambda: {})

        def stream(self, *args, **kwargs):
            return iter(())

    base_llm_module.base_llm = _FakeLLM()
    sys.modules["llm.base_llm"] = base_llm_module
