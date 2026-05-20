# database_request node
# The primary entry-point is the LangGraph subgraph in
# intents/database_request_graph/subgraph.py, invoked directly by app.py.
# This module is kept as a thin wrapper for any non-graph callers.

import os

from intents.database_request_graph.subgraph import database_request_graph_workflow


def handle(text, intent_meta, thread_id, business_id: str = "", high_level_intent: str = "database"):
    """
    Run the database-request subgraph synchronously.
    Prefer calling the subgraph directly from app.py for full
    interrupt (human-in-the-loop) support.
    """

    if not thread_id:
        raise ValueError("Thread Id is missing")

    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {
        "user_query": text,
        "messages": [{"role": "user", "content": text}],
        "sql_retry_count": 0,
        "step_count": 0,
        "max_steps": int(os.getenv("AGENT_MAX_STEPS", "22")),
        "high_level_intent": high_level_intent,
        "business_id": business_id or "",
        "date_range_start": "",
        "date_range_end": "",
        "date_range_description": "",
        "target_tables": [],
        "target_columns": [],
        "entities_valid": False,
        "table_schema": "",
        "generated_sql": "",
        "sql_explanation": "",
        "is_sql_valid": False,
        "sql_validation_error": "",
        "query_results": "[]",
        "execution_error": "",
        "has_results": False,
        "log_entry": "",
        "processed_data": "{}",
        "business_insight": "{}",
        "formatted_response": "",
        "route": "",
    }
    result = database_request_graph_workflow.invoke(initial_state, config=config)
    return result.get("formatted_response", "No response generated.")
