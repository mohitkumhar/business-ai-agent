"""
Metrics Request Subgraph

Graph flow:
  __start__
    → parse_metrics_query       (LLM extracts metric names, PromQL, time range)
    → fetch_metrics             (queries Prometheus HTTP API)
    → analyze_metrics           (LLM analyses the raw metrics data)
    → format_metrics_response   (LLM formats a user-friendly markdown answer)
  __end__
"""

import os

import psycopg
from dotenv import load_dotenv
from intents.metrics_request_graph.graph_state import MetricsRequestGraphState
from intents.metrics_request_graph.utils import (
    analyze_metrics,
    fetch_metrics,
    format_metrics_response,
    parse_metrics_query,
)
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from logger.logger import logger
from psycopg_pool import ConnectionPool

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://admin:root@localhost:5432/test_db"
)


# ── Postgres checkpointer (same pattern as logs graph) ──────────────
def _create_postgres_memory():
    try:
        logger.info("[metrics] Setting up Postgres checkpointer for metrics graph.")
        with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
            PostgresSaver(conn).setup()
        pool = ConnectionPool(conninfo=DATABASE_URL)
        return PostgresSaver(pool)
    except Exception as e:
        logger.error(
            f"[metrics] Failed to set up Postgres checkpointer: {e}", exc_info=True
        )
        raise RuntimeError(
            "Could not set up Postgres checkpointer for metrics graph"
        ) from e


# ── Graph construction ──────────────────────────────────────────────
def generate_graph():
    graph = StateGraph(MetricsRequestGraphState)

    # nodes
    graph.add_node("parse_metrics_query", parse_metrics_query)
    graph.add_node("fetch_metrics", fetch_metrics)
    graph.add_node("analyze_metrics", analyze_metrics)
    graph.add_node("format_metrics_response", format_metrics_response)

    # edges (linear pipeline)
    graph.add_edge(START, "parse_metrics_query")
    graph.add_edge("parse_metrics_query", "fetch_metrics")
    graph.add_edge("fetch_metrics", "analyze_metrics")
    graph.add_edge("analyze_metrics", "format_metrics_response")
    graph.add_edge("format_metrics_response", END)

    memory = _create_postgres_memory()
    workflow = graph.compile(checkpointer=memory)
    return workflow


logger.info("[metrics] Generating metrics request graph workflow...")
metrics_request_graph_workflow = generate_graph()
logger.info("[metrics] Metrics request graph workflow generated successfully.")
