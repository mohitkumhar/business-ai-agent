"""Shared LangGraph → SSE streaming logic for HTTP and Slack (no Flask request object)."""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterator

from langgraph.types import Command

from api_errors import SAFE_INTERNAL_ERROR_MESSAGE
from nodes import intent_detection
from nodes.intent_detection import map_app_intent_to_high_level, order_intents_for_execution
from intents.general_information_graph.subgraph import general_information_graph_workflow
from intents.database_request_graph.subgraph import database_request_graph_workflow
from intents.logs_request_graph.subgraph import logs_request_graph_workflow
from intents.metrics_request_graph.subgraph import metrics_request_graph_workflow

from logger.logger import logger
from logger.agent_debug import utc_iso
from utils.node_timeout import run_with_timeout, MAX_NODE_TIMEOUT_SECONDS


def _build_business_graph_initial_state(
    user_query: str,
    messages: list,
    high_level_intent: str,
    business_id: str,
    chain_prior_summaries: str = "",
) -> dict:
    d = {
        "user_query": user_query,
        "messages": messages,
        "sql_retry_count": 0,
        "step_count": 0,
        "max_steps": int(os.getenv("AGENT_MAX_STEPS", "12")),
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
    if chain_prior_summaries:
        d["chain_prior_summaries"] = chain_prior_summaries
    d["status_updates"] = []
    return d


GREETING_RESPONSE = """Hello! 👋 I'm your Intelligent Business Agent. I can help you with:
• Your revenue, expenses & profit analysis
• Business health checks
• Investment & risk decisions
• Marketing budget advice

What would you like to know about your business today?"""


SSE_NODE_LABELS: dict[str, str] = {
    "__start__": "Starting…",
    "route_entry": "🔍 Routing your request…",
    "out_of_scope": "👋 Preparing a quick reply…",
    "fetch_financial_context": "🗄️ Loading your financial snapshot…",
    "advisory_node": "💡 Preparing personalized advice…",
    "resolve_data_range": "📅 Understanding dates in your question…",
    "validate_entities": "📂 Checking which data you mean…",
    "fetch_table_schema": "📋 Loading schema…",
    "SQL_generation": "🗄️ Querying your business data — building SQL…",
    "SQL_validation": "✅ Validating your query…",
    "execute_query": "⚙️ Running the database query…",
    "logging": "📝 Saving audit log…",
    "post_query_operations": "📊 Summarizing results…",
    "business_insight_generator": "💡 Generating insights…",
    "format_response_of_business_insight_generator": "✨ Almost done — polishing the answer…",
    "standardized_response_formatter": "✅ Finalizing response…",
    "emergency_exit": "⚠️ Wrapping up with partial results…",
    "is_web_search_required": "🔍 Checking whether a web search helps…",
    "answer_user_query": "💡 Preparing business advice…",
    "duck_duck_go_search": "🌐 Searching the web…",
    "format_logs_response": "✨ Formatting log summary…",
    "format_metrics_response": "✨ Formatting metrics…",
    "intent_detection": "🔍 Understanding your question…",
    "intent_chain": "🔗 Continuing your request…",
    "greeting_request": "👋 Loading greeting…",
}


def _db_subgraph_stream_final_nodes(high_level_intent: str) -> list[str]:
    hi = (high_level_intent or "").lower()
    if hi in ("advisory", "hybrid", "out_of_scope"):
        return []
    return ["format_response_of_business_insight_generator"]


def _user_visible_body_from_graph_state(vals: dict) -> str:
    fr = (vals.get("formatted_response") or "").strip()
    if fr:
        return fr
    msgs = vals.get("messages") or []
    for m in reversed(msgs):
        role = getattr(m, "type", None)
        if role is None and isinstance(m, dict):
            role = m.get("role")
        if role not in ("ai", "assistant"):
            continue
        c = getattr(m, "content", None) if not isinstance(m, dict) else m.get("content")
        if isinstance(c, str) and c.strip():
            return c.strip()
        if isinstance(c, list):
            parts: list[str] = []
            for block in c:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(str(block.get("text", "")))
                elif isinstance(block, str):
                    parts.append(block)
            t = "".join(parts).strip()
            if t:
                return t
    sr = vals.get("structured_response")
    if isinstance(sr, str) and sr.strip():
        try:
            o = json.loads(sr)
            s = (o.get("result") or {}).get("summary")
            if isinstance(s, str) and s.strip():
                return s.strip()
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass
    return ""


def _stream_graph(workflow, initial_state, config, intent_dict, final_node_names, resume_input=None):
    intent_str = ",".join(intent_dict["intent"])
    clarification = None
    streamed_chars = 0

    try:
        inputs = Command(resume=resume_input) if resume_input else initial_state

        _start_label = SSE_NODE_LABELS.get("__start__", "Starting…")
        yield f"data: {json.dumps({'type': 'status', 'status': _start_label, 'node': '__start__', 'intent_str': intent_str})}\n\n"
        yield f"data: {json.dumps({'type': 'node_status', 'node': '__start__', 'message': _start_label, 'intent_str': intent_str, 'ts': utc_iso()})}\n\n"

        for event in workflow.stream(inputs, config, stream_mode=["messages", "updates"]):
            mode = event[0]
            if mode == "messages":
                chunk, metadata = event[1]
                node_name = metadata.get("langgraph_node")
                if node_name in final_node_names:
                    content = getattr(chunk, "content", "")
                    if content:
                        streamed_chars += len(content)
                        yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
            elif mode == "updates":
                update_dict = event[1]
                for node_name in update_dict.keys():
                    friendly_name = node_name.replace("_", " ").title()
                    label_msg = SSE_NODE_LABELS.get(
                        node_name,
                        f"✅ Completed: {friendly_name}" if node_name not in final_node_names else "✨ Almost done…",
                    )
                    if node_name not in final_node_names:
                        yield f"data: {json.dumps({'type': 'status', 'status': label_msg, 'node': node_name, 'intent_str': intent_str})}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'status', 'status': label_msg, 'node': node_name, 'intent_str': intent_str})}\n\n"
                    yield f"data: {json.dumps({'type': 'node_status', 'node': node_name, 'message': label_msg, 'intent_str': intent_str, 'ts': utc_iso()})}\n\n"
        state = workflow.get_state(config)
        if state and state.next:
            for task in (state.tasks or []):
                if hasattr(task, "interrupts") and task.interrupts:
                    clarification = task.interrupts[0].value
                    break
            if clarification:
                yield f"data: {json.dumps({'type': 'clarification', 'clarification': clarification, 'intent_str': intent_str})}\n\n"
                return

        vals = getattr(state, "values", None) or {}
        if streamed_chars == 0:
            body = _user_visible_body_from_graph_state(vals)
            if body:
                yield f"data: {json.dumps({'type': 'token', 'content': body})}\n\n"

        yield f"data: {json.dumps({'type': 'final', 'intent_str': intent_str})}\n\n"

    except Exception as exc:
        logger.error(f"Error during stream: {exc}", exc_info=True)
        yield f"data: {json.dumps({'type': 'error', 'error': SAFE_INTERNAL_ERROR_MESSAGE, 'intent_str': intent_str})}\n\n"


def _chain_thread_config(base_thread_id: str, step_index: int) -> dict:
    if step_index == 0:
        return {"configurable": {"thread_id": base_thread_id}}
    return {"configurable": {"thread_id": f"{base_thread_id}__chain_{step_index}"}}


def _artifact_for_chain(result: dict, intent_name: str) -> str:
    if not result:
        return ""
    body = (result.get("formatted_response") or "").strip()
    if not body:
        body = (result.get("user_query_output") or "").strip()
    if not body and result.get("structured_response"):
        try:
            sj = json.loads(result["structured_response"])
            body = (sj.get("result") or {}).get("summary") or ""
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
    if not body:
        body = "(no textual output)"
    return f"### Prior step: {intent_name}\n{body}\n\n"


def _invoke_intent_workflow(
    intent_name: str,
    input_query: str,
    chain_prior: str,
    business_id: str,
    cfg: dict,
) -> dict:
    if intent_name in (
        "database_request",
        "advisory_request",
        "hybrid_request",
        "out_of_scope_request",
    ):
        hl = map_app_intent_to_high_level(intent_name)
        initial = _build_business_graph_initial_state(
            input_query,
            [{"role": "user", "content": input_query}],
            hl,
            business_id,
            chain_prior_summaries=chain_prior,
        )
        return database_request_graph_workflow.invoke(initial, config=cfg)

    if intent_name == "general_information_request":
        initial = {
            "user_query": input_query,
            "messages": [{"role": "user", "content": input_query}],
            "chain_prior_summaries": chain_prior,
        }
        return general_information_graph_workflow.invoke(initial, config=cfg)

    if intent_name == "greeting_request":
        return {
            "formatted_response": GREETING_RESPONSE,
            "user_query_output": GREETING_RESPONSE,
        }

    uq = input_query
    if chain_prior:
        uq = (
            f"{input_query}\n\n---\nContext from earlier steps in this same request:\n{chain_prior}"
        )
    if intent_name == "logs_request":
        initial = {"user_query": uq, "messages": [{"role": "user", "content": uq}]}
        return logs_request_graph_workflow.invoke(initial, config=cfg)
    if intent_name == "metrics_request":
        initial = {"user_query": uq, "messages": [{"role": "user", "content": uq}]}
        return metrics_request_graph_workflow.invoke(initial, config=cfg)

    raise ValueError(f"Unsupported intent for chain: {intent_name}")


def _stream_single_intent(
    intent_name: str,
    input_query: str,
    chain_prior: str,
    business_id: str,
    intent_dict: dict,
    cfg: dict,
):
    if intent_name in (
        "database_request",
        "advisory_request",
        "hybrid_request",
        "out_of_scope_request",
    ):
        hl = map_app_intent_to_high_level(intent_name)
        stream_nodes = _db_subgraph_stream_final_nodes(hl)
        initial = _build_business_graph_initial_state(
            input_query,
            [{"role": "user", "content": input_query}],
            hl,
            business_id,
            chain_prior_summaries=chain_prior,
        )
        yield from _stream_graph(
            database_request_graph_workflow,
            initial,
            cfg,
            intent_dict,
            stream_nodes,
        )
        return

    if intent_name == "general_information_request":
        initial = {
            "user_query": input_query,
            "messages": [{"role": "user", "content": input_query}],
            "chain_prior_summaries": chain_prior,
        }
        yield from _stream_graph(
            general_information_graph_workflow,
            initial,
            cfg,
            intent_dict,
            ["answer_user_query"],
        )
        return

    if intent_name == "greeting_request":
        intent_str = ",".join(intent_dict["intent"])
        glabel = SSE_NODE_LABELS.get("greeting_request", "👋 Loading greeting…")
        yield f"data: {json.dumps({'type': 'status', 'status': glabel, 'node': 'greeting_request', 'intent_str': intent_str})}\n\n"
        yield f"data: {json.dumps({'type': 'node_status', 'node': 'greeting_request', 'message': glabel, 'intent_str': intent_str, 'ts': utc_iso()})}\n\n"
        yield f"data: {json.dumps({'type': 'token', 'content': GREETING_RESPONSE})}\n\n"
        yield f"data: {json.dumps({'type': 'final', 'intent_str': intent_str})}\n\n"
        return

    uq = input_query
    if chain_prior:
        uq = (
            f"{input_query}\n\n---\nContext from earlier steps in this same request:\n{chain_prior}"
        )

    if intent_name == "logs_request":
        initial = {"user_query": uq, "messages": [{"role": "user", "content": uq}]}
        yield from _stream_graph(
            logs_request_graph_workflow,
            initial,
            cfg,
            intent_dict,
            ["format_logs_response"],
        )
        return

    if intent_name == "metrics_request":
        initial = {"user_query": uq, "messages": [{"role": "user", "content": uq}]}
        yield from _stream_graph(
            metrics_request_graph_workflow,
            initial,
            cfg,
            intent_dict,
            ["format_metrics_response"],
        )
        return

    raise ValueError(f"Unsupported intent for stream: {intent_name}")


_SUPPORTED_CHAIN = frozenset(
    {
        "database_request",
        "advisory_request",
        "hybrid_request",
        "out_of_scope_request",
        "general_information_request",
        "logs_request",
        "metrics_request",
        "greeting_request",
    }
)


def stream_agent_sse_lines(
    input_query: str,
    thread_id: str,
    business_id: str = "",
    *,
    on_chain_intent: Callable[[str], None] | None = None,
) -> Iterator[str]:
    """Yield Server-Sent Event lines (``data: {...}\\n\\n``) for the agent run."""
    config = {"configurable": {"thread_id": thread_id}}

    try:
        logger.info(f"Checking for pending interrupts for thread_id: '{thread_id}'")
        snapshot = database_request_graph_workflow.get_state(config)
        if snapshot and snapshot.next:
            logger.info(
                f"Pending interrupt found for thread_id: '{thread_id}'. Resuming database_request graph."
            )
            intent_dict = {"intent": ["database_request"]}
            yield from _stream_graph(
                database_request_graph_workflow,
                None,
                config,
                intent_dict,
                _db_subgraph_stream_final_nodes("database"),
                resume_input=input_query,
            )
            return
    except Exception as e:
        logger.warning(
            f"Error checking for pending interrupt for thread_id '{thread_id}': {e}",
            exc_info=True,
        )

    logger.info(f"No pending interrupt for thread_id: '{thread_id}'. Starting intent detection.")
    intent = intent_detection.detect_intent(input_query)
    ordered = order_intents_for_execution(intent.get("intent") or [])
    intent["intent"] = ordered
    logger.info(f"Detected intent(s) for query '{input_query}': {ordered}")

    for intent_name in ordered:
        if intent_name not in _SUPPORTED_CHAIN:
            logger.warning(
                "Unsupported intent in chain '%s' for query: '%s'", intent_name, input_query
            )
            yield f"data: {json.dumps({'type': 'error', 'error': f'Intent {intent_name} is not supported.', 'intent_str': ','.join(ordered)})}\n\n"
            return

    def generate_chained():
        prior = ""
        n = len(ordered)
        intent_dict = {"intent": ordered}
        intent_str_joined = ",".join(ordered)
        id_label = SSE_NODE_LABELS.get("intent_detection", "🔍 Understanding your question…")
        yield f"data: {json.dumps({'type': 'status', 'status': id_label, 'node': 'intent_detection', 'intent_str': intent_str_joined})}\n\n"
        yield f"data: {json.dumps({'type': 'node_status', 'node': 'intent_detection', 'message': id_label, 'intent_str': intent_str_joined, 'ts': utc_iso()})}\n\n"
        yield f"data: {json.dumps({'type': 'chain_start', 'intents': ordered, 'total_steps': n})}\n\n"

        for idx, intent_name in enumerate(ordered):
            logger.info("Chain step %s/%s: %s for thread_id=%s", idx + 1, n, intent_name, thread_id)
            if on_chain_intent:
                on_chain_intent(intent_name)
            cfg = _chain_thread_config(thread_id, idx)
            yield f"data: {json.dumps({'type': 'status', 'status': f'Running step {idx + 1} of {n}: {intent_name}', 'node': 'intent_chain', 'intent_str': ','.join(ordered)})}\n\n"

            is_last = idx == n - 1
            if not is_last:
                try:
                    result = run_with_timeout(
                        lambda iname=intent_name, pr=prior, c=cfg: _invoke_intent_workflow(
                            iname, input_query, pr, business_id, c
                        ),
                        MAX_NODE_TIMEOUT_SECONDS,
                    )
                except TimeoutError as exc:
                    logger.error(
                        "Chained invoke timed out at %s: %s",
                        intent_name,
                        exc,
                        exc_info=True,
                    )
                    yield f"data: {json.dumps({'type': 'error', 'error': str(exc), 'intent_str': intent_name})}\n\n"
                    return

                except Exception as exc:
                    logger.error("Chained invoke failed at %s: %s", intent_name, exc, exc_info=True)
                    yield f"data: {json.dumps({'type': 'error', 'error': str(exc), 'intent_str': intent_name})}\n\n"
                    return
                artifact = _artifact_for_chain(result, intent_name)
                prior = (prior + artifact).strip()
                yield f"data: {json.dumps({'type': 'chain_step_complete', 'intent': intent_name, 'index': idx, 'intent_str': ','.join(ordered)})}\n\n"
            else:
                try:
                    yield from _stream_single_intent(
                        intent_name,
                        input_query,
                        prior,
                        business_id,
                        intent_dict,
                        cfg,
                    )
                except Exception as exc:
                    logger.error("Chained stream failed at %s: %s", intent_name, exc, exc_info=True)
                    yield f"data: {json.dumps({'type': 'error', 'error': str(exc), 'intent_str': intent_name})}\n\n"

    yield from generate_chained()