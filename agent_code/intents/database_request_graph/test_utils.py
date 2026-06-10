import pytest
from unittest.mock import MagicMock, patch
from pydantic import BaseModel, Field, ValidationError

# Import the helper function from your utils file
from intents.database_request_graph.utils import invoke_with_retry


class DummyStructuredOutput(BaseModel):
    summary: str = Field(..., description="A simple test outcome")


def _make_validation_error():
    try:
        DummyStructuredOutput(summary=None) # Intentional missing field
    except ValidationError as e:
        return e


def test_invoke_with_retry_recovers_on_second_attempt():
    class FakeStructuredLLM:
        def __init__(self):
            self.call_count = 0

        def invoke(self, prompt: str):
            self.call_count += 1
            if self.call_count == 1:
                raise _make_validation_error()
            return DummyStructuredOutput(summary="Success on try 2!")

    fake_llm = FakeStructuredLLM()
    result = invoke_with_retry(fake_llm, prompt="Test prompt", retries=2)
    
    assert result.summary == "Success on try 2!"
    assert fake_llm.call_count == 2


def test_zero_retries_raises_immediately_on_failure():
    fake_llm = MagicMock()
    fake_llm.invoke.side_effect = _make_validation_error()

    with patch("intents.database_request_graph.utils.time.sleep"):
        with pytest.raises(ValidationError):
            invoke_with_retry(fake_llm, "query", retries=0)
            
    # FIXED Line 270: Added the missing assert keyword
    assert fake_llm.invoke.call_count == 1