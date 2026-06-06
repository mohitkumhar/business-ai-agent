import sys
import types
import pytest
from unittest.mock import patch

_langgraph = types.ModuleType("langgraph")
_langgraph_graph = types.ModuleType("langgraph.graph")
_langgraph_graph_message = types.ModuleType("langgraph.graph.message")
_langgraph_graph_message.add_messages = lambda x, y: x + y

_fake_modules = {
    "langgraph": _langgraph,
    "langgraph.graph": _langgraph_graph,
    "langgraph.graph.message": _langgraph_graph_message,
}

with patch.dict(sys.modules, _fake_modules):
    from agent_code.intents.metrics_request_graph.graph_state import MetricsRequestGraphState


class TestMetricsRequestGraphState:
    """Tests for MetricsRequestGraphState TypedDict."""

    def test_can_instantiate_with_all_fields(self):
        """All fields should be accepted and stored correctly."""
        state: MetricsRequestGraphState = {
            "user_query": "Show me CPU usage for the last hour",
            "messages": [{"role": "user", "content": "CPU usage"}],
            "metric_names": ["cpu_usage"],
            "promql_queries": ["avg(rate(cpu_seconds_total[5m]))"],
            "lookback_minutes": 60,
            "step_seconds": 30,
            "time_range_description": "Last 1 hour",
            "raw_metrics": '{"status":"success","data":{"result":[]}}',
            "fetch_error": "",
            "has_results": False,
            "metrics_analysis": "",
            "formatted_response": "",
        }
        assert state["user_query"] == "Show me CPU usage for the last hour"
        assert state["messages"] == [{"role": "user", "content": "CPU usage"}]
        assert state["metric_names"] == ["cpu_usage"]
        assert state["promql_queries"] == ["avg(rate(cpu_seconds_total[5m]))"]
        assert state["lookback_minutes"] == 60
        assert state["step_seconds"] == 30
        assert state["time_range_description"] == "Last 1 hour"
        assert state["raw_metrics"] == '{"status":"success","data":{"result":[]}}'
        assert state["fetch_error"] == ""
        assert state["has_results"] is False
        assert state["metrics_analysis"] == ""
        assert state["formatted_response"] == ""

    def test_minimal_instantiation(self):
        """Basic state with only required fields (all fields are required per TypedDict)."""
        state: MetricsRequestGraphState = {
            "user_query": "test",
            "messages": [],
            "metric_names": [],
            "promql_queries": [],
            "lookback_minutes": 0,
            "step_seconds": 0,
            "time_range_description": "",
            "raw_metrics": "",
            "fetch_error": "",
            "has_results": False,
            "metrics_analysis": "",
            "formatted_response": "",
        }
        assert state["user_query"] == "test"
        assert state["messages"] == []
        assert state["metric_names"] == []

    def test_messages_field_stores_list(self):
        """messages should accept a list and can be extended."""
        state: MetricsRequestGraphState = {
            "user_query": "test",
            "messages": [],
            "metric_names": [],
            "promql_queries": [],
            "lookback_minutes": 0,
            "step_seconds": 0,
            "time_range_description": "",
            "raw_metrics": "",
            "fetch_error": "",
            "has_results": False,
            "metrics_analysis": "",
            "formatted_response": "",
        }
        state["messages"].append({"role": "assistant", "content": "Hello"})
        assert len(state["messages"]) == 1
        assert state["messages"][0]["role"] == "assistant"

    def test_error_fields_can_hold_strings(self):
        """fetch_error should accept error messages."""
        state: MetricsRequestGraphState = {
            "user_query": "test",
            "messages": [],
            "metric_names": [],
            "promql_queries": [],
            "lookback_minutes": 0,
            "step_seconds": 0,
            "time_range_description": "",
            "raw_metrics": "",
            "fetch_error": "Connection timeout",
            "has_results": False,
            "metrics_analysis": "",
            "formatted_response": "",
        }
        assert state["fetch_error"] == "Connection timeout"

    def test_has_results_boolean(self):
        """has_results should be a boolean."""
        state: MetricsRequestGraphState = {
            "user_query": "test",
            "messages": [],
            "metric_names": [],
            "promql_queries": [],
            "lookback_minutes": 0,
            "step_seconds": 0,
            "time_range_description": "",
            "raw_metrics": "",
            "fetch_error": "",
            "has_results": True,
            "metrics_analysis": "",
            "formatted_response": "",
        }
        assert state["has_results"] is True