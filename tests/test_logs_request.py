from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest
import requests

from intents.logs_request_graph.utils import fetch_logs


@patch("intents.logs_request_graph.utils.requests.get")
def test_fetch_logs_success(mock_get):
    # Mock a successful response from Loki
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "status": "success",
        "data": {
            "resultType": "streams",
            "result": [
                {
                    "stream": {"job": "python_app"},
                    "values": [
                        ["1680000000000000000", "2026-05-31 12:00:02 - intent_detection - INFO - app.py:12 - handle - Message 2"],
                        ["1680000000000000000", "2026-05-31 12:00:01 - intent_detection - INFO - app.py:10 - handle - Message 1"],
                    ]
                }
            ]
        }
    }
    mock_get.return_value = mock_resp

    state = {
        "user_query": "show me logs",
        "log_query": '{job="python_app"}',
        "lookback_minutes": 60,
        "limit": 100,
    }

    result = fetch_logs(state)

    assert result["has_results"] is True
    assert result["log_line_count"] == 2
    # Verify chronological re-sorting (oldest first, i.e. lines reversed since direction was backward)
    expected_logs = (
        "2026-05-31 12:00:01 - intent_detection - INFO - app.py:10 - handle - Message 1\n"
        "2026-05-31 12:00:02 - intent_detection - INFO - app.py:12 - handle - Message 2"
    )
    assert result["raw_logs"] == expected_logs
    assert result["fetch_error"] == ""


@patch("intents.logs_request_graph.utils.requests.get")
def test_fetch_logs_timeout(mock_get):
    # Mock a timeout exception
    mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

    state = {
        "user_query": "show me logs",
        "log_query": '{job="python_app"}',
        "lookback_minutes": 60,
        "limit": 100,
    }

    result = fetch_logs(state)

    assert result["has_results"] is False
    assert result["log_line_count"] == 0
    assert result["raw_logs"] == ""
    assert "Timed out fetching logs" in result["fetch_error"]


@patch("intents.logs_request_graph.utils.requests.get")
def test_fetch_logs_connection_error(mock_get):
    # Mock a connection error exception
    mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

    state = {
        "user_query": "show me logs",
        "log_query": '{job="python_app"}',
        "lookback_minutes": 60,
        "limit": 100,
    }

    result = fetch_logs(state)

    assert result["has_results"] is False
    assert result["log_line_count"] == 0
    assert result["raw_logs"] == ""
    assert "Cannot connect to Loki" in result["fetch_error"]
