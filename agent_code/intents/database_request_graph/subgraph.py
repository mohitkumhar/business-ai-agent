"""
Database / advisory unified subgraph

Flow:
  START → route_entry → (conditional)
    - emergency_exit → END
    - out_of_scope → END
    - fetch_financial_context → advisory_node → standardized_response_formatter → END
    - resolve_data_range → … → format_response → standardized_response_formatter → END
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv
import psycopg
from logger.logger import logger
import os
from intents.database_request_graph.graph_state import DatabaseRequestGraphState
from intents.database_request_graph.utils import (
    resolve_data_range,
    validate_entities,
    fetch_table_schema,
    sql_generation,
    sql_validation,
    execute_query,
    logging_node,
    post_query_operations,
    business_insight_generator,
    format_response_of_business_insight_generator,
)
from intents.database_request_graph.step_utils import wrap_node, route_emergency_or
from intents.database_request_graph.advisory_nodes import (
    route_entry_node,
    fetch_financial_context,
    advisory_node,
    out_of_scope_node,
    emergency_exit_node,
    standardized_response_formatter,
)

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://admin:root@localhost:5432/test_db"
)


AVAILABLE_TABLES: list[str] = [
    "alerts",
    "business_health_scores",
    "businesses",
    "daily_transactions",
    "decision_outcomes",
    "decisions",
    "employees",
    "financial_records",
    "products",
    "roles",
    "users",
]

TABLE_DESCRIPTIONS: dict[str, str] = {
    "alerts": "Business alerts with severity (Low/Medium/High) and status (Active/Resolved)",
    "business_health_scores": "Overall business health metrics - cash, profitability, growth, cost-control, risk scores",
    "businesses": "Business registration — name, industry, owner, monthly_target_revenue, risk_appetite",

    "daily_transactions": "Daily revenue & expense transactions with categories and amounts",
    "decision_outcomes": "Outcomes of past decisions with actual profit impact",
    "decisions": "Business decisions (Marketing/Hiring/Pricing/Expansion) with risk levels and success probability",
    "employees": "Employee records - name, role, salary, status (Active/Left)",
    "financial_records": "Monthly financial summaries — total_revenue, total_expenses, net_profit, cash_balance, loans_due (month/year)",
    "products": "Product catalog - cost price, selling price, stock quantity",
    "roles": "Roles defined for each business",
    "users": "System users with email, password hash, and role",
}


def _route_after_sql_validation(state: DatabaseRequestGraphState) -> str:
    try:
        if state.get("halt_pipeline") or state.get("emergency_reason"):
            return "emergency_exit"
        logger.info(f"Routing after SQL validation. State: {state}")
        return state.get("route", "sql_valid")
    except Exception as e:
        logger.error(f"Error in routing function after SQL validation: {e}", exc_info=True)
        return "sql_valid"


def _route_after_entry(state: DatabaseRequestGraphState) -> str:
    if state.get("halt_pipeline") or state.get("emergency_reason"):
        return "emergency_exit"
    hi = (state.get("high_level_intent") or "database").lower()
    if hi == "out_of_scope":
        return "out_of_scope"
    if hi in ("advisory", "hybrid"):
        return "fetch_financial_context"
    return "resolve_data_range"


def _route_after_fetch(state: DatabaseRequestGraphState) -> str:
    if state.get("halt_pipeline") or state.get("emergency_reason"):
        return "emergency_exit"
    return "advisory_node"


def _route_after_advisory(state: DatabaseRequestGraphState) -> str:
    if state.get("halt_pipeline") or state.get("emergency_reason"):
        return "emergency_exit"
    return "standardized_response_formatter"


def _create_postgres_memory():
    if os.getenv("USE_IN_MEMORY_CHECKPOINTER") == "true":
        logger.info("Using in-memory checkpointer for database request graph.")
        return MemorySaver()

    try:
        logger.info("Setting up Postgres checkpointer for graph state persistence.")
        with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
            PostgresSaver(conn).setup()
        pool = ConnectionPool(conninfo=DATABASE_URL)
        return PostgresSaver(pool)
    except Exception as e:
        logger.error(f"Failed to set up Postgres checkpointer: {e}", exc_info=True)
        raise RuntimeError("Could not set up Postgres checkpointer") from e


def generate_graph():
    graph = StateGraph(DatabaseRequestGraphState)

    # wrapped database nodes (step budget)
    graph.add_node("route_entry", route_entry_node)
    graph.add_node("out_of_scope", wrap_node(out_of_scope_node))
    graph.add_node("fetch_financial_context", wrap_node(fetch_financial_context))
    graph.add_node("advisory_node", wrap_node(advisory_node))
    graph.add_node("emergency_exit", emergency_exit_node)
    graph.add_node("standardized_response_formatter", wrap_node(standardized_response_formatter))

    graph.add_node("resolve_data_range", wrap_node(resolve_data_range))
    graph.add_node("validate_entities", wrap_node(validate_entities))
    graph.add_node("fetch_table_schema", wrap_node(fetch_table_schema))
    graph.add_node("SQL_generation", wrap_node(sql_generation))
    graph.add_node("SQL_validation", wrap_node(sql_validation))
    graph.add_node("execute_query", wrap_node(execute_query))
    graph.add_node("logging", wrap_node(logging_node))
    graph.add_node("post_query_operations", wrap_node(post_query_operations))
    graph.add_node("business_insight_generator", wrap_node(business_insight_generator))
    graph.add_node(
        "format_response_of_business_insight_generator",
        wrap_node(format_response_of_business_insight_generator),
    )

    graph.add_edge(START, "route_entry")
    graph.add_conditional_edges(
        "route_entry",
        _route_after_entry,
        {
            "emergency_exit": "emergency_exit",
            "out_of_scope": "out_of_scope",
            "fetch_financial_context": "fetch_financial_context",
            "resolve_data_range": "resolve_data_range",
        },
    )

    graph.add_edge("out_of_scope", END)

    graph.add_conditional_edges(
        "fetch_financial_context",
        _route_after_fetch,
        {"emergency_exit": "emergency_exit", "advisory_node": "advisory_node"},
    )
    graph.add_conditional_edges(
        "advisory_node",
        _route_after_advisory,
        {
            "emergency_exit": "emergency_exit",
            "standardized_response_formatter": "standardized_response_formatter",
        },
    )

    graph.add_conditional_edges(
        "resolve_data_range",
        route_emergency_or("validate_entities"),
        {"emergency_exit": "emergency_exit", "validate_entities": "validate_entities"},
    )
    graph.add_conditional_edges(
        "validate_entities",
        route_emergency_or("fetch_table_schema"),
        {"emergency_exit": "emergency_exit", "fetch_table_schema": "fetch_table_schema"},
    )
    graph.add_conditional_edges(
        "fetch_table_schema",
        route_emergency_or("SQL_generation"),
        {"emergency_exit": "emergency_exit", "SQL_generation": "SQL_generation"},
    )
    graph.add_conditional_edges(
        "SQL_generation",
        route_emergency_or("SQL_validation"),
        {"emergency_exit": "emergency_exit", "SQL_validation": "SQL_validation"},
    )

    graph.add_conditional_edges(
        "SQL_validation",
        _route_after_sql_validation,
        {
            "sql_valid": "execute_query",
            "sql_invalid": "SQL_generation",
            "sql_failed": "emergency_exit",
            "emergency_exit": "emergency_exit",
        },
    )

    graph.add_conditional_edges(
        "execute_query",
        route_emergency_or("logging"),
        {"emergency_exit": "emergency_exit", "logging": "logging"},
    )
    graph.add_conditional_edges(
        "logging",
        route_emergency_or("post_query_operations"),
        {"emergency_exit": "emergency_exit", "post_query_operations": "post_query_operations"},
    )
    graph.add_conditional_edges(
        "post_query_operations",
        route_emergency_or("business_insight_generator"),
        {
            "emergency_exit": "emergency_exit",
            "business_insight_generator": "business_insight_generator",
        },
    )
    graph.add_conditional_edges(
        "business_insight_generator",
        route_emergency_or("format_response_of_business_insight_generator"),
        {
            "emergency_exit": "emergency_exit",
            "format_response_of_business_insight_generator": "format_response_of_business_insight_generator",
        },
    )
    graph.add_conditional_edges(
        "format_response_of_business_insight_generator",
        route_emergency_or("standardized_response_formatter"),
        {
            "emergency_exit": "emergency_exit",
            "standardized_response_formatter": "standardized_response_formatter",
        },
    )

    graph.add_edge("standardized_response_formatter", END)
    graph.add_edge("emergency_exit", END)

    memory = _create_postgres_memory()
    workflow = graph.compile(checkpointer=memory)
    return workflow


logger.info("Generating database request graph workflow...")
database_request_graph_workflow = generate_graph()
logger.info("Database / advisory graph workflow generated successfully.")
