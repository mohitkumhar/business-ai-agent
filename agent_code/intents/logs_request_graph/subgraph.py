"""
Logs Request Subgraph

Graph flow:
  __start__
    → parse_logs_query       (LLM converts user question → LogQL + time params)
    → fetch_logs             (queries Loki HTTP API)
    → analyze_logs           (LLM analyses the raw log lines)
    → format_logs_response   (LLM formats a user-friendly markdown answer)
  __end__
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv
import psycopg
import os

from logger.logger import logger
from intents.logs_request_graph.graph_state import LogsRequestGraphState
from intents.logs_request_graph.utils import (
    parse_logs_query,
    fetch_logs,
    analyze_logs,
    format_logs_response,
)

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://admin:root@localhost:5432/test_db"
)


# ── Postgres checkpointer (same pattern as metrics graph) ───────────────
def _create_postgres_memory():
    if os.getenv("USE_IN_MEMORY_CHECKPOINTER") == "true":
        logger.info("[logs] Using in-memory checkpointer for logs graph.")
        return MemorySaver()

    try:
        logger.info("[logs] Setting up Postgres checkpointer for logs graph.")
        with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
            PostgresSaver(conn).setup()
        pool = ConnectionPool(conninfo=DATABASE_URL)
        return PostgresSaver(pool)
    except Exception as e:
        logger.error(
            f"[logs] Failed to set up Postgres checkpointer: {e}", exc_info=True
        )
        raise RuntimeError(
            "Could not set up Postgres checkpointer for logs graph"
        ) from e


# ── Graph construction ──────────────────────────────────────────────────
def generate_graph():
    graph = StateGraph(LogsRequestGraphState)

    # nodes
    graph.add_node("parse_logs_query", parse_logs_query)
    graph.add_node("fetch_logs", fetch_logs)
    graph.add_node("analyze_logs", analyze_logs)
    graph.add_node("format_logs_response", format_logs_response)

    # edges (linear pipeline)
    graph.add_edge(START, "parse_logs_query")
    graph.add_edge("parse_logs_query", "fetch_logs")
    graph.add_edge("fetch_logs", "analyze_logs")
    graph.add_edge("analyze_logs", "format_logs_response")
    graph.add_edge("format_logs_response", END)

    memory = _create_postgres_memory()
    workflow = graph.compile(checkpointer=memory)
    return workflow


logger.info("[logs] Generating logs request graph workflow...")
logs_request_graph_workflow = generate_graph()
logger.info("[logs] Logs request graph workflow generated successfully.")
