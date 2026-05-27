from __future__ import annotations

from dataclasses import dataclass

from agent_code.nodes import format_response as response_module


def test_serialize_returns_strings_unchanged():
    assert response_module._serialize("already formatted") == "already formatted"


def test_serialize_handles_dicts_and_non_json_primitives():
    rendered = response_module._serialize({"amount": 12, "items": [1, 2]})

    assert '"amount": 12' in rendered
    assert '"items": [' in rendered


def test_format_response_greeting_skips_llm(monkeypatch):
    class RaisingLLM:
        def invoke(self, prompt):
            raise AssertionError("LLM should not be called for greetings")

    monkeypatch.setattr(response_module, "base_llm", RaisingLLM())

    response = response_module.format_response("greeting", {"hello": "there"})

    assert response["status"] == "ok"
    assert response["intent"] == "greeting"
    assert '"hello": "there"' in response["result"]


def test_format_response_uses_llm_content_when_available(monkeypatch):
    @dataclass
    class LLMResponse:
        content: str

    class FakeLLM:
        def invoke(self, prompt):
            assert "Raw data" in prompt
            return LLMResponse("polished answer")

    monkeypatch.setattr(response_module, "base_llm", FakeLLM())

    response = response_module.format_response("database", [{"x": 1}])

    assert response["result"] == "polished answer"


def test_format_response_falls_back_to_raw_data_on_llm_error(monkeypatch):
    class FailingLLM:
        def invoke(self, prompt):
            raise RuntimeError("offline")

    monkeypatch.setattr(response_module, "base_llm", FailingLLM())

    response = response_module.format_response("database", {"x": 1})

    assert '"x": 1' in response["result"]


def test_format_response_stream_returns_greeting_output_directly(monkeypatch):
    chunks = list(
        response_module.format_response_stream(
            {"intent": ["greeting_request"]},
            {"user_query_output": "hello"},
        )
    )

    assert chunks == ["hello"]


def test_format_response_stream_returns_general_information_directly():
    chunks = list(
        response_module.format_response_stream(
            {"intent": ["general_information_request"]},
            {"user_query_output": "plain answer"},
        )
    )

    assert chunks == ["plain answer"]


def test_format_response_stream_yields_llm_chunks(monkeypatch):
    @dataclass
    class Chunk:
        content: str

    class FakeLLM:
        def stream(self, prompt):
            yield Chunk("part ")
            yield Chunk("two")

    monkeypatch.setattr(response_module, "base_llm", FakeLLM())

    chunks = list(response_module.format_response_stream("database", {"x": 1}))

    assert chunks == ["part ", "two"]


def test_format_response_stream_falls_back_to_raw_text(monkeypatch):
    class FailingLLM:
        def stream(self, prompt):
            raise RuntimeError("offline")

    monkeypatch.setattr(response_module, "base_llm", FailingLLM())

    chunks = list(response_module.format_response_stream("database", {"x": 1}))

    assert len(chunks) == 1
    assert '"x": 1' in chunks[0]
