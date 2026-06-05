import sys
from unittest.mock import MagicMock, patch
import pytest

# ── Block heavy dependencies ──
sys.modules['langgraph.checkpoint.postgres'] = MagicMock()
sys.modules['langgraph.checkpoint.memory'] = MagicMock()
sys.modules['psycopg'] = MagicMock()
sys.modules['psycopg_pool'] = MagicMock()
sys.modules['logger'] = MagicMock()
sys.modules['logger.logger'] = MagicMock()
sys.modules['intents.logs_request_graph.utils'] = MagicMock()

# ── Patch the validation that blocks mock checkpoints ──
def _allow_any_checkpointer(checkpointer):
    return checkpointer

# ── Import the original function ──
with patch('langgraph.types.ensure_valid_checkpointer', side_effect=_allow_any_checkpointer):
    with patch('agent_code.intents.logs_request_graph.subgraph.StateGraph.compile', return_value=MagicMock(invoke=MagicMock())):
        from agent_code.intents.logs_request_graph.subgraph import (
            generate_graph,
            _create_postgres_memory,
        )


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
        # First call: PostgresSaver(conn) → mock with setup()
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
        with patch('langgraph.types.ensure_valid_checkpointer', side_effect=_allow_any_checkpointer):
            with patch('agent_code.intents.logs_request_graph.subgraph._create_postgres_memory', return_value=MagicMock()):
                with patch('agent_code.intents.logs_request_graph.subgraph.StateGraph.compile', return_value=MagicMock(invoke=MagicMock())):
                    workflow = generate_graph()
                    assert hasattr(workflow, "invoke") or hasattr(workflow, "ainvoke")