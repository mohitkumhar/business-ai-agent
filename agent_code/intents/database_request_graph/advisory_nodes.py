"""Advisory, hybrid, out-of-scope, emergency exit, and standardized JSON responses."""
from __future__ import annotations

import json
import os
import re
from typing import Any

from langchain_core.runnables import RunnableConfig
from dotenv import load_dotenv

from logger.logger import logger
from llm.base_llm import base_llm
from db_config import execute_read_query
from intents.database_request_graph.graph_state import DatabaseRequestGraphState
from intents.database_request_graph.step_utils import step_guard

load_dotenv()

_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _log_query_failure(operation: str, table_name: str, exc: Exception) -> None:
    logger.warning(
        "Database query failed | operation=%s table=%s error_type=%s error_message=%s",
        operation,
        table_name,
        type(exc).__name__,
        str(exc),
        exc_info=True,
    )


def _resolve_business_id(state: DatabaseRequestGraphState) -> str:
    try:
        raw = (state.get("business_id") or os.getenv("DEFAULT_BUSINESS_ID") or "").strip()
        if raw and _UUID_PATTERN.match(raw):
            return raw
        for table_name, sql in (
            ("businesses", "SELECT business_id FROM businesses LIMIT 1"),
            ("business", "SELECT business_id FROM business LIMIT 1"),
        ):
            try:
                rows = execute_read_query(sql)
                if rows and len(rows) > 0:
                    return str(rows[0].get("business_id", ""))
            except Exception as exc:
                _log_query_failure(
                    operation="resolve_business_id_lookup",
                    table_name=table_name,
                    exc=exc,
                )
                continue
        return ""
    except Exception as e:
        logger.warning(
            "[WARN] Could not resolve business_id. operation=%s error_type=%s error_message=%s. Proceeding without it.",
            "resolve_business_id",
            type(e).__name__,
            str(e),
            exc_info=True,
        )
        return ""


def route_entry_node(state: DatabaseRequestGraphState):
    """First node: bump step budget and pass through (routing via conditional edges)."""
    from logger.agent_debug import log_node_enter, log_node_exit

    t0 = log_node_enter(
        "route_entry",
        {**state, "intent": state.get("high_level_intent", "unknown")},
        "Routing your request through the business agent pipeline…",
    )
    g = step_guard(state)
    log_node_exit("route_entry", {**state, **g}, t0, route_key="route")
    return g


def fetch_financial_context(state: DatabaseRequestGraphState):
    """Load recent financial snapshot for advisory / hybrid (parameterized by business_id)."""
    bid = _resolve_business_id(state)
    if not bid or not _UUID_PATTERN.match(bid):
        logger.warning("fetch_financial_context: no business_id; returning empty context")
        return {
            "financial_context": json.dumps(
                {"error": "no_business", "message": "No business record found for context."}
            ),
        }

    business_profile: dict | None = None
    for table_name, profile_sql in (
        (
            "businesses",
            f"""
SELECT business_id, business_name, industry_type, owner_name,
       monthly_target_revenue, risk_appetite
FROM businesses
WHERE business_id = '{bid}'::uuid
LIMIT 1
""".strip(),
        ),
        (
            "business",
            f"""
SELECT business_id, business_name, industry_type, owner_name,
       monthly_target_revenue, risk_appetite
FROM business
WHERE business_id = '{bid}'::uuid
LIMIT 1
""".strip(),
        ),
    ):
        try:
            prof_rows = execute_read_query(profile_sql)
            if prof_rows:
                business_profile = prof_rows[0]
                break
        except Exception as exc:
            _log_query_failure(
                operation="fetch_financial_context_profile_lookup",
                table_name=table_name,
                exc=exc,
            )
            continue

    sql = f"""
SELECT
  fr.business_id,
  b.business_name,
  fr.total_revenue,
  fr.total_expenses,
  fr.net_profit,
  fr.cash_balance,
  fr.loans_due,
  fr.month,
  fr.year
FROM financial_records fr
INNER JOIN businesses b ON fr.business_id = b.business_id
WHERE fr.business_id = '{bid}'::uuid
ORDER BY fr.year DESC, fr.month DESC
LIMIT 24
""".strip()
    sql_fallback = f"""
SELECT
  fr.business_id,
  b.business_name,
  fr.total_revenue,
  fr.total_expenses,
  fr.net_profit,
  fr.cash_balance,
  fr.loans_due,
  fr.month,
  fr.year
FROM financial_records fr
INNER JOIN business b ON fr.business_id = b.business_id
WHERE fr.business_id = '{bid}'::uuid
ORDER BY fr.year DESC, fr.month DESC
LIMIT 24
""".strip()
    try:
        try:
            rows = execute_read_query(sql)
        except Exception as exc:
            _log_query_failure(
                operation="fetch_financial_context_primary_query",
                table_name="financial_records + businesses",
                exc=exc,
            )
            try:
                rows = execute_read_query(sql_fallback)
            except Exception as fallback_exc:
                _log_query_failure(
                    operation="fetch_financial_context_fallback_query",
                    table_name="financial_records + business",
                    exc=fallback_exc,
                )
                raise
        payload = {
            "business_id": bid,
            "business_profile": business_profile,
            "rows": rows,
            "row_count": len(rows),
        }
        logger.info(
            "fetch_financial_context: business_profile=%s, %s month rows for business %s",
            bool(business_profile),
            len(rows),
            bid,
        )
        return {"financial_context": json.dumps(payload, default=str)}
    except Exception as exc:
        logger.error("fetch_financial_context failed: %s", exc, exc_info=True)
        return {
            "financial_context": json.dumps(
                {
                    "error": str(exc),
                    "business_id": bid,
                    "business_profile": business_profile,
                    "rows": [],
                },
                default=str,
            ),
        }


def out_of_scope_node(state: DatabaseRequestGraphState, config: RunnableConfig):
    """Polite rejection — no DB access."""
    msg = (
        "I’m focused on helping with your business data, advice about money and operations, "
        "and questions tied to your company’s information. "
        "I can’t help with general trivia, weather, jokes, or unrelated topics — but ask me "
        "about revenue, costs, hiring, loans, or strategy and I’ll dive in."
    )
    envelope = _envelope(
        status="out_of_scope",
        intent="out_of_scope",
        user_query=state.get("user_query", ""),
        summary=msg,
        data=None,
        recommendations=[],
        risk_level=None,
        follow_ups=[
            "What was my revenue last month?",
            "Should I take on a loan for expansion?",
        ],
    )
    return {
        "structured_response": json.dumps(envelope, ensure_ascii=False),
        "formatted_response": msg,
        "messages": [{"role": "assistant", "content": msg}],
        "query_understood": state.get("user_query", ""),
    }


def advisory_node(state: DatabaseRequestGraphState, config: RunnableConfig):
    """LLM advisory using financial_context (advisory or hybrid)."""
    user_query = state.get("user_query", "")
    ctx_raw = state.get("financial_context", "{}")
    mode = state.get("high_level_intent", "advisory")
    try:
        ctx = json.loads(ctx_raw)
    except (json.JSONDecodeError, TypeError):
        ctx = {"raw": ctx_raw}

    risk_line = ""
    if mode == "hybrid":
        risk_line = (
            "You must also give a qualitative risk_level: low, medium, or high, "
            "and 1–2 sentences on runway / affordability based only on the numbers provided."
        )

    prior = (state.get("chain_prior_summaries") or "").strip()
    prior_block = ""
    if prior:
        prior_block = f"""
Earlier in this same user request, other assistants already answered related parts. Use this as ground truth alongside the JSON below; resolve contradictions only if numbers disagree (prefer the JSON snapshot for current books):
{prior}
"""

    prompt = f"""You are an experienced small-business advisor.

Owner question: "{user_query}"
{prior_block}
Latest financial context from their system (JSON). Use only these figures plus prudent assumptions — do not invent specific amounts not shown:
{json.dumps(ctx, indent=2, default=str)}

Context fields:
- business_profile: registered business row (e.g. monthly_target_revenue, risk_appetite, industry_type). Use these for concrete budget guidance when financial rows are thin.
- rows: recent monthly financial_records (total_revenue, total_expenses, net_profit, cash_balance, loans_due, month, year). Quote these numbers when present.
- row_count: number of monthly rows; 0 means no history yet, but business_profile may still have targets.

Respond as JSON with keys (these fields are turned into markdown for the user — keep them concrete and tied to their question):
  "query_understood": short plain-English restatement of what they asked,
  "summary": 1–3 sentences directly answering them (this becomes the main "Answer" section),
  "recommendations": array of 2–5 actionable strings,
  "risk_level": one of "low"|"medium"|"high"|null,
  "follow_up_questions": array of 1–3 helpful follow-ups.

{risk_line}
Rules: prefer ₹ for currency if amounts are INR-style; be concise.
- If business_profile and/or rows contain numbers, you MUST base your answer on them (e.g. marketing budget as % of latest total_revenue or of monthly_target_revenue). Do not claim you have "no financial data" when row_count > 0 or business_profile is non-null.
- If row_count is 0 but business_profile exists, use monthly_target_revenue and risk_appetite for grounded guidance.
- Only ask for more data if both business_profile is missing and row_count is 0.
Do not wrap the JSON in markdown code fences."""

    parsed: dict = {}
    try:
        response = base_llm.invoke(prompt, config=config)
        content = (response.content or "").strip()
        parsed = _parse_json_loose(content)
        understood = parsed.get("query_understood") or user_query
        summary = parsed.get("summary") or content
        recs = parsed.get("recommendations", [])
        if not isinstance(recs, list):
            recs = []
        risk = parsed.get("risk_level")
        if risk not in ("low", "medium", "high", None):
            risk = None
        follow = parsed.get("follow_up_questions", [])
        if not isinstance(follow, list):
            follow = []
    except Exception as exc:
        logger.error("advisory_node LLM failed: %s", exc, exc_info=True)
        understood = user_query
        summary = "I could not complete advisory analysis right now. Please try again shortly."
        recs = ["Retry your question with any specific numbers you know."]
        risk = None
        follow = []
        parsed = {}

    stat = "advisory" if mode == "advisory" else "success"
    envelope = _envelope(
        status=stat,
        intent="hybrid" if mode == "hybrid" else "advisory",
        user_query=user_query,
        summary=summary,
        data=ctx if isinstance(ctx, dict) else None,
        recommendations=recs,
        risk_level=risk,
        follow_ups=follow,
        query_understood_val=understood,
    )
    user_md = _advisory_to_markdown(
        user_query=user_query,
        understood=understood,
        summary=summary,
        recs=recs,
        risk=risk,
        follow=follow,
    )
    return {
        "advisory_result": json.dumps(parsed, default=str),
        "structured_response": json.dumps(envelope, ensure_ascii=False),
        "formatted_response": user_md,
        "messages": [{"role": "assistant", "content": user_md}],
        "query_understood": understood,
    }


def _advisory_to_markdown(
    *,
    user_query: str,
    understood: str,
    summary: str,
    recs: list,
    risk: str | None,
    follow: list,
) -> str:
    """User-facing markdown from parsed advisory JSON (not the raw JSON blob)."""
    uq = (user_query or "").strip()
    und = (understood or uq).strip()
    lines = [
        f"**Your question:** {uq}",
        "",
        f"**How I understood it:** {und}",
        "",
        "## Answer",
        "",
    ]
    body = (summary or "").strip()
    lines.append(body if body else "_I could not produce a short summary — see below._")
    if risk in ("low", "medium", "high"):
        lines.extend(["", f"**Risk level:** {risk.title()}"])
    if recs:
        lines.extend(["", "## Recommendations", ""])
        for r in recs:
            lines.append(f"- {r}")
    if follow:
        lines.extend(["", "## Follow-up questions", ""])
        for q in follow:
            lines.append(f"- {q}")
    return "\n".join(lines).strip()


def _parse_json_loose(text: str) -> dict:
    text = text.strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    if "{" in text and "}" in text:
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            return {}
    return {}


def emergency_exit_node(state: DatabaseRequestGraphState):
    """Max steps or exhausted SQL retries — partial structured response."""
    partial: dict[str, Any] = {
        "user_query": state.get("user_query"),
        "generated_sql": state.get("generated_sql"),
        "sql_validation_error": state.get("sql_validation_error"),
        "query_results": state.get("query_results"),
        "execution_error": state.get("execution_error"),
        "emergency_reason": state.get("emergency_reason"),
        "step_count": state.get("step_count"),
    }
    inner = {
        "status": "partial",
        "message": "I was unable to fully process your request. Here is what I found so far.",
        "partial_result": partial,
        "suggestion": "Please try rephrasing your question.",
    }
    envelope = _envelope(
        status="partial",
        intent=state.get("high_level_intent", "database"),
        user_query=state.get("user_query", ""),
        summary=inner["message"],
        data=partial,
        recommendations=[inner["suggestion"]],
        risk_level="medium",
        follow_ups=["Can you simplify your question?", "Try asking for a single month of revenue."],
        query_understood_val=state.get("user_query", ""),
    )
    envelope["result"]["data"] = inner
    user_msg = (
        f"{inner['message']}\n\n"
        f"*{inner['suggestion']}*"
    )
    return {
        "structured_response": json.dumps(envelope, ensure_ascii=False),
        "formatted_response": user_msg,
        "messages": [{"role": "assistant", "content": user_msg}],
        "halt_pipeline": True,
    }


def standardized_response_formatter(state: DatabaseRequestGraphState, config: RunnableConfig):
    """Ensure final envelope exists for database path; merge insight + processed_data."""
    if state.get("structured_response"):
        return {}
    user_query = state.get("user_query", "")
    execution_error = state.get("execution_error", "")
    insight_raw = state.get("business_insight", "{}")
    proc_raw = state.get("processed_data", "{}")
    try:
        insight = json.loads(insight_raw)
    except (json.JSONDecodeError, TypeError):
        insight = {}
    try:
        proc = json.loads(proc_raw)
    except (json.JSONDecodeError, TypeError):
        proc = {}

    if execution_error:
        envelope = _envelope(
            status="error",
            intent="database",
            user_query=user_query,
            summary=f"Could not run your query: {execution_error}",
            data=None,
            recommendations=["Rephrase the question or narrow the date range."],
            risk_level="medium",
            follow_ups=["Show revenue for last month", "List my top expense categories"],
            query_understood_val=user_query,
        )
    elif proc.get("status") == "no_data":
        envelope = _envelope(
            status="success",
            intent="database",
            user_query=user_query,
            summary=insight.get("summary") or proc.get("message", "No matching records."),
            data=[],
            recommendations=insight.get("recommendations", []),
            risk_level=None,
            follow_ups=["Try a wider date range", "Ask for a different metric"],
            query_understood_val=user_query,
        )
    else:
        recs = insight.get("recommendations", [])
        if not isinstance(recs, list):
            recs = []
        risks = insight.get("risk_flags", [])
        risk_level = "high" if risks else "low"
        envelope = _envelope(
            status="success",
            intent="database",
            user_query=user_query,
            summary=insight.get("summary", "Here is what we found in your data."),
            data=proc.get("data"),
            recommendations=recs,
            risk_level=risk_level if risks else None,
            follow_ups=[
                "What drove the biggest expenses?",
                "How does this compare to last quarter?",
            ],
            query_understood_val=user_query,
        )

    formatted = state.get("formatted_response") or envelope["result"]["summary"]
    return {
        "structured_response": json.dumps(envelope, ensure_ascii=False),
        "formatted_response": formatted,
    }


def _envelope(
    *,
    status: str,
    intent: str,
    user_query: str,
    summary: str,
    data: Any,
    recommendations: list,
    risk_level: str | None,
    follow_ups: list,
    query_understood_val: str | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "intent": intent,
        "query_understood": query_understood_val or user_query,
        "result": {
            "summary": summary,
            "data": data,
            "recommendations": recommendations,
            "risk_level": risk_level,
        },
        "follow_up_questions": follow_ups,
    }
