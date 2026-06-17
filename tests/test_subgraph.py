import sys
from unittest.mock import MagicMock, patch
import pytest

_fake_modules = {
    "langgraph": MagicMock(),
    "langgraph.graph": MagicMock(),
    "langgraph.graph.message": MagicMock(),
    "langgraph.types": MagicMock(),
    "langgraph.checkpoint.postgres": MagicMock(),
    "langgraph.checkpoint.memory": MagicMock(),
    "psycopg": MagicMock(),
    "psycopg_pool": MagicMock(),
    "logger": MagicMock(),
    "logger.logger": MagicMock(),
    "intents.logs_request_graph.utils": MagicMock(),
    "intents.logs_request_graph.graph_state": MagicMock(),
    "intents.logs_request_graph": MagicMock(),
    "intents": MagicMock(),
}

def _allow_any_checkpointer(checkpointer):
    return checkpointer

with patch.dict(sys.modules, _fake_modules):
    from agent_code.intents.logs_request_graph.subgraph import (
        generate_graph,
        _create_postgres_memory,
    )
    import agent_code.intents.logs_request_graph.subgraph as _subgraph_module

# Keep the subgraph module registered so @patch can find it
sys.modules["agent_code.intents.logs_request_graph.subgraph"] = _subgraph_module


class TestCreatePostgresMemory:
    @patch.dict("os.environ", {"USE_IN_MEMORY_CHECKPOINTER": "true"}, clear=True)
    @patch("agent_code.intents.logs_request_graph.subgraph.MemorySaver")
    def test_returns_in_memory_saver_when_env_set(self, mock_memory_saver):
        mock_memory_saver.return_value = "in-memory-checkpointer"
        result = _create_postgres_memory()
        assert result == "in-memory-checkpointer"

    @patch.dict("os.environ", {"USE_IN_MEMORY_CHECKPOINTER": "false", "DATABASE_URL": "postgresql://test"}, clear=True)
    @patch("agent_code.intents.logs_request_graph.subgraph.ConnectionPool")
    @patch("agent_code.intents.logs_request_graph.subgraph.psycopg.connect")
    @patch("agent_code.intents.logs_request_graph.subgraph.PostgresSaver")
    def test_returns_postgres_saver_when_db_available(
        self, mock_postgres_saver, mock_connect, mock_pool
    ):
        mock_conn = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        saver_mock = MagicMock()
        mock_postgres_saver.side_effect = [saver_mock, "postgres-checkpointer"]
        result = _create_postgres_memory()
        assert result == "postgres-checkpointer"
        saver_mock.setup.assert_called_once()

    @patch.dict("os.environ", {"USE_IN_MEMORY_CHECKPOINTER": "false", "DATABASE_URL": "postgresql://test"}, clear=True)
    @patch("agent_code.intents.logs_request_graph.subgraph.psycopg.connect")
    def test_raises_runtime_error_on_db_failure(self, mock_connect):
        mock_connect.side_effect = Exception("Connection refused")
        with pytest.raises(RuntimeError, match="Could not set up Postgres checkpointer"):
            _create_postgres_memory()


class TestGenerateGraph:
    def test_graph_can_be_compiled(self):
        with patch("agent_code.intents.logs_request_graph.subgraph._create_postgres_memory", return_value=MagicMock()):
            with patch("agent_code.intents.logs_request_graph.subgraph.StateGraph.compile", return_value=MagicMock(invoke=MagicMock())):
                workflow = generate_graph()
                assert hasattr(workflow, "invoke") or hasattr(workflow, "ainvoke")
