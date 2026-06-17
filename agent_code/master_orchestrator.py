"""
Main Parent Orchestrator Agent
Routes incoming requests to the appropriate specialized subgraph worker.
"""

import os
import sys
from typing import TypedDict, Optional, Any, Dict
from langgraph.graph import StateGraph, START, END

# Ensure parent directory is in path for seamless imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# 1. IMPORT YOUR SUBGRAPHS
from intents.database_request_graph.subgraph import database_request_graph_workflow
from intents.general_information_graph.subgraph import gen_info_graph_workflow
from intents.logs_request_graph.subgraph import logs_graph_workflow
from intents.metrics_request_graph.subgraph import metrics_graph_workflow


# 2. DEFINE THE ROOT STATE SCHEMA
class MasterOrchestratorState(TypedDict):
    user_query: str
    selected_intent: str  # Options: 'database', 'general_info', 'logs', 'metrics'
    response: Optional[str]
    # Catch-all dictionary to safely receive unique keys returned from worker subgraphs
    final_output_payload: Optional[Dict[str, Any]]


# 3. DEFINE THE ROUTER NODE
def intent_classifier_node(state: MasterOrchestratorState) -> Dict[str, Any]:
    """
    Analyzes the user_query to determine which specialized subgraph
    should handle the business request.
    """
    query = state["user_query"].lower()
    
    if "log" in query or "history" in query:
        intent = "logs"
    elif "metric" in query or "performance" in query or "score" in query:
        intent = "metrics"
    elif "info" in query or "about" in query or "help" in query:
        intent = "general_info"
    else:
        intent = "database"
        
    return {"selected_intent": intent}


def route_to_subgraph(state: MasterOrchestratorState) -> str:
    """Returns the targeted intent destination step."""
    return state.get("selected_intent", "database")


# 4. DEFINE THE AGGREGATOR NODE (Handles the "Return" logic)
def response_aggregator_node(state: MasterOrchestratorState) -> Dict[str, Any]:
    """
    Inspects the final state of the executed subgraph, extracts the result text,
    and returns it inside the parent 'response' key.
    """
    # Look for common response keys used across your different subgraphs
    possible_keys = ["processed_data", "summary", "final_response", "output", "response"]
    extracted_response = None

    for key in possible_keys:
        if state.get(key):
            extracted_response = state[key]
            break

    # Fallback message if the worker subgraph didn't write to an expected key
    if not extracted_response:
        extracted_response = f"Successfully processed request inside the {state.get('selected_intent')} subsystem."

    return {"response": extracted_response}


# 5. BUILD THE MASTER STATE GRAPH ARCHITECTURE
master_builder = StateGraph(MasterOrchestratorState)

# Register workflow nodes
master_builder.add_node("intent_classifier", intent_classifier_node)
master_builder.add_node("response_aggregator", response_aggregator_node)

# Register your subgraphs as structural worker nodes
master_builder.add_node("database_worker", database_request_graph_workflow)
master_builder.add_node("general_info_worker", gen_info_graph_workflow)
master_builder.add_node("logs_worker", logs_graph_workflow)
master_builder.add_node("metrics_worker", metrics_graph_workflow)

# Build edge connections
master_builder.add_edge(START, "intent_classifier")

master_builder.add_conditional_edges(
    "intent_classifier",
    route_to_subgraph,
    {
        "database": "database_worker",
        "general_info": "general_info_worker",
        "logs": "logs_worker",
        "metrics": "metrics_worker",
    }
)

# Route all worker graph outputs into the aggregator instead of ending abruptly
master_builder.add_edge("database_worker", "response_aggregator")
master_builder.add_edge("general_info_worker", "response_aggregator")
master_builder.add_edge("logs_worker", "response_aggregator")
master_builder.add_edge("metrics_worker", "response_aggregator")

# The aggregator passes the structured answer to the end of the graph lifecycle
master_builder.add_edge("response_aggregator", END)

# Compile the complete system application
unified_agent = master_builder.compile()