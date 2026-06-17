"""Regression tests for agent_code/intents/database_request_graph/advisory_nodes.py

Run from the agent_code directory:
    python -m pytest tests/test_advisory_nodes.py -v
"""
from __future__ import annotations

import json
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Stub out all heavy third-party imports so the module loads without a full
# LangChain / DB / dotenv environment.
# ---------------------------------------------------------------------------

def _make_stub(name: str):
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod


for _pkg in [
    "langchain_core",
    "langchain_core.runnables",
    "dotenv",
]:
    _make_stub(_pkg)

sys.modules["langchain_core.runnables"].RunnableConfig = dict  # type: ignore

_dotenv = sys.modules["dotenv"]
_dotenv.load_dotenv = lambda: None  # type: ignore

# Stub project-local modules
for _local in ["api_errors", "logger", "logger.logger", "llm", "llm.base_llm",
               "db_config", "intents", "intents.database_request_graph",
               "intents.database_request_graph.graph_state",
               "intents.database_request_graph.step_utils"]:
    _make_stub(_local)

sys.modules["api_errors"].SAFE_INTERNAL_ERROR_MESSAGE = "internal_error"  # type: ignore
_logger_mod = sys.modules["logger.logger"]
_logger_mod.logger = MagicMock()  # type: ignore

_llm_mod = sys.modules["llm.base_llm"]
_llm_mod.base_llm = MagicMock()  # type: ignore

sys.modules["db_config"].execute_read_query = MagicMock()  # type: ignore

_gs_mod = sys.modules["intents.database_request_graph.graph_state"]
_gs_mod.DatabaseRequestGraphState = dict  # type: ignore

_su_mod = sys.modules["intents.database_request_graph.step_utils"]
_su_mod.step_guard = MagicMock(return_value={})  # type: ignore

# Now safe to import the real module
import importlib
import os

import importlib.util, pathlib

_SRC = pathlib.Path(__file__).parent.parent / "intents" / "database_request_graph" / "advisory_nodes.py"

spec = importlib.util.spec_from_file_location("advisory_nodes", str(_SRC))
advisory_nodes = importlib.util.module_from_spec(spec)  # type: ignore
spec.loader.exec_module(advisory_nodes)  # type: ignore

_parse_json_loose = advisory_nodes._parse_json_loose
_envelope = advisory_nodes._envelope
_advisory_to_markdown = advisory_nodes._advisory_to_markdown
_resolve_business_id = advisory_nodes._resolve_business_id
out_of_scope_node = advisory_nodes.out_of_scope_node
emergency_exit_node = advisory_nodes.emergency_exit_node
standardized_response_formatter = advisory_nodes.standardized_response_formatter


# ===========================================================================
# 1. _parse_json_loose
# ===========================================================================

class TestParseJsonLoose(unittest.TestCase):

    def test_valid_json_object(self):
        result = _parse_json_loose('{"key": "value", "num": 42}')
        self.assertEqual(result, {"key": "value", "num": 42})

    def test_valid_json_with_whitespace(self):
        result = _parse_json_loose('  \n{"a": 1}  \n')
        self.assertEqual(result, {"a": 1})

    def test_json_wrapped_in_markdown_fence(self):
        text = '```json\n{"summary": "ok"}\n```'
        result = _parse_json_loose(text)
        self.assertEqual(result, {"summary": "ok"})

    def test_json_with_leading_text(self):
        text = 'Here is the result: {"answer": true}'
        result = _parse_json_loose(text)
        self.assertEqual(result, {"answer": True})

    def test_empty_string_returns_empty_dict(self):
        self.assertEqual(_parse_json_loose(""), {})

    def test_whitespace_only_returns_empty_dict(self):
        self.assertEqual(_parse_json_loose("   "), {})

    def test_no_braces_returns_empty_dict(self):
        self.assertEqual(_parse_json_loose("no JSON here at all"), {})

    def test_malformed_json_returns_empty_dict(self):
        self.assertEqual(_parse_json_loose("{bad json: value}"), {})

    def test_nested_object(self):
        payload = '{"outer": {"inner": [1, 2, 3]}}'
        result = _parse_json_loose(payload)
        self.assertEqual(result["outer"]["inner"], [1, 2, 3])


# ===========================================================================
# 2. _envelope
# ===========================================================================

class TestEnvelope(unittest.TestCase):

    def _make(self, **overrides):
        defaults = dict(
            status="success",
            intent="advisory",
            user_query="What is my profit?",
            summary="Your profit is ₹50k.",
            data={"rows": []},
            recommendations=["Cut costs"],
            risk_level="low",
            follow_ups=["Compare to last quarter?"],
        )
        defaults.update(overrides)
        return _envelope(**defaults)

    def test_top_level_keys_present(self):
        env = self._make()
        for key in ("status", "intent", "query_understood", "result", "follow_up_questions"):
            self.assertIn(key, env)

    def test_result_subkeys_present(self):
        env = self._make()
        for key in ("summary", "data", "recommendations", "risk_level"):
            self.assertIn(key, env["result"])

    def test_status_passed_through(self):
        env = self._make(status="error")
        self.assertEqual(env["status"], "error")

    def test_query_understood_uses_override(self):
        env = _envelope(
            status="success",
            intent="advisory",
            user_query="raw query",
            summary="s",
            data=None,
            recommendations=[],
            risk_level=None,
            follow_ups=[],
            query_understood_val="rephrased query",
        )
        self.assertEqual(env["query_understood"], "rephrased query")

    def test_query_understood_falls_back_to_user_query(self):
        env = self._make()
        self.assertEqual(env["query_understood"], "What is my profit?")

    def test_risk_level_stored_in_result(self):
        env = self._make(risk_level="high")
        self.assertEqual(env["result"]["risk_level"], "high")

    def test_risk_level_none_allowed(self):
        env = self._make(risk_level=None)
        self.assertIsNone(env["result"]["risk_level"])

    def test_follow_ups_stored(self):
        env = self._make(follow_ups=["q1", "q2"])
        self.assertEqual(env["follow_up_questions"], ["q1", "q2"])

    def test_data_none_allowed(self):
        env = self._make(data=None)
        self.assertIsNone(env["result"]["data"])


# ===========================================================================
# 3. _advisory_to_markdown
# ===========================================================================

class TestAdvisoryToMarkdown(unittest.TestCase):

    def _make(self, **overrides):
        defaults = dict(
            user_query="How is my cash flow?",
            understood="Cash-flow health check",
            summary="Cash balance is healthy at ₹2L.",
            recs=["Reduce ad-hoc expenses", "Invoice faster"],
            risk="low",
            follow=["What is my runway?"],
        )
        defaults.update(overrides)
        return _advisory_to_markdown(**defaults)

    def test_contains_user_question(self):
        md = self._make()
        self.assertIn("How is my cash flow?", md)

    def test_contains_understood_line(self):
        md = self._make()
        self.assertIn("Cash-flow health check", md)

    def test_contains_answer_heading(self):
        md = self._make()
        self.assertIn("## Answer", md)

    def test_contains_summary(self):
        md = self._make()
        self.assertIn("Cash balance is healthy", md)

    def test_risk_level_shown_when_valid(self):
        for level in ("low", "medium", "high"):
            with self.subTest(level=level):
                md = self._make(risk=level)
                self.assertIn(f"**Risk level:** {level.title()}", md)

    def test_risk_level_not_shown_when_none(self):
        md = self._make(risk=None)
        self.assertNotIn("Risk level", md)

    def test_recommendations_section_shown(self):
        md = self._make()
        self.assertIn("## Recommendations", md)
        self.assertIn("- Reduce ad-hoc expenses", md)

    def test_no_recommendations_section_when_empty(self):
        md = self._make(recs=[])
        self.assertNotIn("## Recommendations", md)

    def test_follow_up_section_shown(self):
        md = self._make()
        self.assertIn("## Follow-up questions", md)
        self.assertIn("- What is my runway?", md)

    def test_no_follow_up_section_when_empty(self):
        md = self._make(follow=[])
        self.assertNotIn("## Follow-up questions", md)

    def test_empty_summary_shows_placeholder(self):
        md = self._make(summary="")
        self.assertIn("_I could not produce a short summary", md)

    def test_understood_falls_back_to_user_query_when_empty(self):
        md = _advisory_to_markdown(
            user_query="my query",
            understood="",
            summary="ok",
            recs=[],
            risk=None,
            follow=[],
        )
        self.assertIn("my query", md)


# ===========================================================================
# 4. _resolve_business_id
# ===========================================================================

_VALID_UUID = "12345678-1234-1234-1234-123456789abc"
_INVALID_UUID = "not-a-uuid"


class TestResolveBusinessId(unittest.TestCase):

    def test_valid_uuid_in_state(self):
        state = {"business_id": _VALID_UUID}
        result = _resolve_business_id(state)
        self.assertEqual(result, _VALID_UUID)

    def test_invalid_uuid_in_state_falls_through(self):
        state = {"business_id": _INVALID_UUID}
        with patch.object(advisory_nodes, "execute_read_query", return_value=[]):
            result = _resolve_business_id(state)
        self.assertEqual(result, "")

    def test_env_var_used_when_state_empty(self):
        state = {}
        with patch.dict(os.environ, {"DEFAULT_BUSINESS_ID": _VALID_UUID}):
            result = _resolve_business_id(state)
        self.assertEqual(result, _VALID_UUID)

    def test_db_fallback_when_no_state_or_env(self):
        state = {}
        mock_row = {"business_id": _VALID_UUID}
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(advisory_nodes, "execute_read_query", return_value=[mock_row]):
                result = _resolve_business_id(state)
        self.assertEqual(result, _VALID_UUID)

    def test_db_failure_returns_empty_string(self):
        state = {}
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(advisory_nodes, "execute_read_query", side_effect=Exception("DB down")):
                result = _resolve_business_id(state)
        self.assertEqual(result, "")

    def test_empty_state_no_env_no_db_returns_empty(self):
        state = {}
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(advisory_nodes, "execute_read_query", return_value=[]):
                result = _resolve_business_id(state)
        self.assertEqual(result, "")


# ===========================================================================
# 5. out_of_scope_node
# ===========================================================================

class TestOutOfScopeNode(unittest.TestCase):

    def _call(self, user_query="Tell me a joke"):
        state = {"user_query": user_query}
        return out_of_scope_node(state, config={})

    def test_returns_structured_response(self):
        result = self._call()
        self.assertIn("structured_response", result)

    def test_structured_response_is_valid_json(self):
        result = self._call()
        parsed = json.loads(result["structured_response"])
        self.assertIsInstance(parsed, dict)

    def test_status_is_out_of_scope(self):
        result = self._call()
        parsed = json.loads(result["structured_response"])
        self.assertEqual(parsed["status"], "out_of_scope")

    def test_intent_is_out_of_scope(self):
        result = self._call()
        parsed = json.loads(result["structured_response"])
        self.assertEqual(parsed["intent"], "out_of_scope")

    def test_formatted_response_present(self):
        result = self._call()
        self.assertIn("formatted_response", result)
        self.assertIsInstance(result["formatted_response"], str)

    def test_messages_list_present(self):
        result = self._call()
        self.assertIn("messages", result)
        self.assertIsInstance(result["messages"], list)
        self.assertEqual(result["messages"][0]["role"], "assistant")

    def test_query_understood_echoes_user_query(self):
        result = self._call(user_query="What is 2+2?")
        self.assertEqual(result["query_understood"], "What is 2+2?")

    def test_follow_up_questions_non_empty(self):
        result = self._call()
        parsed = json.loads(result["structured_response"])
        self.assertGreater(len(parsed["follow_up_questions"]), 0)

    def test_empty_user_query(self):
        result = self._call(user_query="")
        self.assertIn("structured_response", result)


# ===========================================================================
# 6. emergency_exit_node
# ===========================================================================

class TestEmergencyExitNode(unittest.TestCase):

    def _state(self, **kwargs):
        base = {
            "user_query": "Show my expenses",
            "generated_sql": "SELECT * FROM x",
            "sql_validation_error": None,
            "query_results": None,
            "execution_error": "timeout",
            "emergency_reason": "max_steps",
            "step_count": 10,
            "high_level_intent": "database",
        }
        base.update(kwargs)
        return base

    def test_returns_structured_response(self):
        result = emergency_exit_node(self._state())
        self.assertIn("structured_response", result)

    def test_status_is_partial(self):
        result = emergency_exit_node(self._state())
        parsed = json.loads(result["structured_response"])
        self.assertEqual(parsed["status"], "partial")

    def test_halt_pipeline_is_true(self):
        result = emergency_exit_node(self._state())
        self.assertTrue(result["halt_pipeline"])

    def test_formatted_response_contains_suggestion(self):
        result = emergency_exit_node(self._state())
        self.assertIn("rephrasing", result["formatted_response"])

    def test_messages_role_is_assistant(self):
        result = emergency_exit_node(self._state())
        self.assertEqual(result["messages"][0]["role"], "assistant")

    def test_partial_data_embedded_in_envelope(self):
        result = emergency_exit_node(self._state())
        parsed = json.loads(result["structured_response"])
        inner = parsed["result"]["data"]
        self.assertEqual(inner["status"], "partial")
        self.assertIn("partial_result", inner)

    def test_risk_level_is_medium(self):
        result = emergency_exit_node(self._state())
        parsed = json.loads(result["structured_response"])
        self.assertEqual(parsed["result"]["risk_level"], "medium")

    def test_empty_state_does_not_raise(self):
        try:
            emergency_exit_node({})
        except Exception as exc:
            self.fail(f"emergency_exit_node raised unexpectedly: {exc}")


# ===========================================================================
# 7. standardized_response_formatter
# ===========================================================================

class TestStandardizedResponseFormatter(unittest.TestCase):

    def test_no_op_when_structured_response_exists(self):
        state = {"structured_response": '{"status":"success"}'}
        result = standardized_response_formatter(state, config={})
        self.assertEqual(result, {})

    def test_error_path(self):
        state = {
            "user_query": "Get revenue",
            "execution_error": "syntax error near SELECT",
            "business_insight": "{}",
            "processed_data": "{}",
        }
        result = standardized_response_formatter(state, config={})
        parsed = json.loads(result["structured_response"])
        self.assertEqual(parsed["status"], "error")
        self.assertIn("syntax error", parsed["result"]["summary"])

    def test_no_data_path(self):
        state = {
            "user_query": "Revenue in Jan",
            "execution_error": "",
            "business_insight": json.dumps({"summary": "No records found.", "recommendations": []}),
            "processed_data": json.dumps({"status": "no_data", "message": "No records found."}),
        }
        result = standardized_response_formatter(state, config={})
        parsed = json.loads(result["structured_response"])
        self.assertEqual(parsed["status"], "success")
        self.assertEqual(parsed["result"]["data"], [])

    def test_success_path_with_risk_flags(self):
        state = {
            "user_query": "Profit summary",
            "execution_error": "",
            "business_insight": json.dumps({
                "summary": "Profit is down 10%.",
                "recommendations": ["Review expenses"],
                "risk_flags": ["negative_trend"],
            }),
            "processed_data": json.dumps({"data": [{"month": 1, "net_profit": -5000}]}),
        }
        result = standardized_response_formatter(state, config={})
        parsed = json.loads(result["structured_response"])
        self.assertEqual(parsed["status"], "success")
        self.assertEqual(parsed["result"]["risk_level"], "high")
        self.assertIn("Review expenses", parsed["result"]["recommendations"])

    def test_success_path_no_risk_flags(self):
        state = {
            "user_query": "Revenue",
            "execution_error": "",
            "business_insight": json.dumps({
                "summary": "Revenue is up.",
                "recommendations": [],
                "risk_flags": [],
            }),
            "processed_data": json.dumps({"data": [{"month": 2, "total_revenue": 100000}]}),
        }
        result = standardized_response_formatter(state, config={})
        parsed = json.loads(result["structured_response"])
        self.assertIsNone(parsed["result"]["risk_level"])

    def test_malformed_insight_json_handled(self):
        state = {
            "user_query": "Expenses",
            "execution_error": "",
            "business_insight": "NOT JSON",
            "processed_data": json.dumps({"data": []}),
        }
        try:
            result = standardized_response_formatter(state, config={})
            self.assertIn("structured_response", result)
        except Exception as exc:
            self.fail(f"Should not raise on bad insight JSON: {exc}")

    def test_malformed_processed_data_handled(self):
        state = {
            "user_query": "Loans",
            "execution_error": "",
            "business_insight": "{}",
            "processed_data": "BAD JSON",
        }
        try:
            result = standardized_response_formatter(state, config={})
            self.assertIn("structured_response", result)
        except Exception as exc:
            self.fail(f"Should not raise on bad processed_data JSON: {exc}")


if __name__ == "__main__":
    unittest.main(verbosity=2)