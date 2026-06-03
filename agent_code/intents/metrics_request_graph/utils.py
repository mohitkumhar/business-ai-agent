"""
Node functions for the Metrics-Request LangGraph subgraph.

Graph flow:
  parse_metrics_query  ->  fetch_metrics  ->  analyze_metrics  ->  format_metrics_response
"""

import json
import os
import time
import requests
from datetime import date
from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig

from llm.base_llm import base_llm
from logger.logger import logger
from intents.metrics_request_graph.graph_state import MetricsRequestGraphState
from intents.metrics_request_graph.structures import (
    MetricsQueryParseOutput,
    MetricsAnalysisOutput,
)

load_dotenv()

# Prometheus connection
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")

# LLMs with structured output
metrics_query_parse_llm = base_llm.with_structured_output(MetricsQueryParseOutput)
metrics_analysis_llm = base_llm.with_structured_output(MetricsAnalysisOutput)


# ── Available metrics reference (fed to the LLM for better query generation) ──
AVAILABLE_METRICS = """
## Web Dashboard (web-dashboard:5001)
- web_http_requests_total{method, endpoint, status}  — HTTP request counter
- web_request_duration_seconds{method, endpoint} — HTTP request latency histogram
- chat_messages_total{role}                      — Chat messages sent (user/assistant)
- chat_agent_latency_seconds                     — Round-trip time to the agent API
- active_chat_conversations                      — Gauge of active conversations
- dashboard_api_errors_total{endpoint}           — Dashboard API error counter

## Backend Agent (backend:5000)
- agent_requests_total{method, endpoint, status} — Agent API request counter
- agent_request_duration_seconds{method, endpoint} — Agent API latency histogram
- agent_intent_detections_total{intent}          — Intent detection counter by type
- agent_intent_processing_seconds{intent}        — Intent processing latency histogram
- agent_errors_total{intent, error_type}         — Agent error counter
"""


# NODE 1 – parse_metrics_query
# =================================

def parse_metrics_query(state: MetricsRequestGraphState):
    """Use the LLM to determine which Prometheus metrics and PromQL queries
    are relevant to the user's question."""

    user_query = state["user_query"]
    today_str = date.today().isoformat()

    logger.info(f"[metrics] Parsing metrics query: '{user_query}'")

    prompt = f"""You are a Prometheus metrics query assistant.
Today's date is {today_str}.

The following Prometheus metrics are available:
{AVAILABLE_METRICS}

The user wants to inspect application metrics. Based on their query, produce:

1. **metric_names** – list of relevant Prometheus metric names from the catalogue above.
2. **promql_queries** – one or more valid PromQL expressions to answer the user's question.
   - For counters, apply rate() or increase() as appropriate.
   - For histograms, consider histogram_quantile() for percentiles.
   - For gauges, a plain query or avg_over_time() works.
   - If the user is vague (e.g., "show me metrics", "how is the system doing"),
     generate a broad set of queries covering request rates, latencies, and error rates.
3. **lookback_minutes** – how far back to look:
     "last 5 minutes" -> 5
     "last hour"      -> 60
     "last 24 hours"  -> 1440
     Default to 60 if unspecified.
4. **step_seconds** – resolution step. Default 15. Use 60 for ranges >6h, 300 for >24h.
5. **time_range_description** – human-readable time range description.

User Query: {user_query}"""

    try:
        result = metrics_query_parse_llm.invoke(prompt)
        logger.info(f"[metrics] Parsed metrics query: {result}")
        return {
            "metric_names": result.metric_names,
            "promql_queries": result.promql_queries,
            "lookback_minutes": result.lookback_minutes,
            "step_seconds": result.step_seconds,
            "time_range_description": result.time_range_description,
        }
    except Exception as exc:
        logger.error(f"[metrics] parse_metrics_query failed: {exc}", exc_info=True)
        # Sensible defaults — broad overview
        return {
            "metric_names": ["agent_requests_total", "web_http_requests_total"],
            "promql_queries": [
                "rate(agent_requests_total[5m])",
                "rate(web_http_requests_total[5m])",
            ],
            "lookback_minutes": 60,
            "step_seconds": 15,
            "time_range_description": "Last 60 minutes (default – could not parse query)",
        }


# NODE 2 – fetch_metrics (Prometheus HTTP API)
# =================================

def fetch_metrics(state: MetricsRequestGraphState):
    """Execute each PromQL query against the Prometheus HTTP API and collect
    the results into a single JSON string."""

    promql_queries = state.get("promql_queries", [])
    lookback_minutes = state.get("lookback_minutes", 60)
    step_seconds = state.get("step_seconds", 15)

    end_ts = time.time()
    start_ts = end_ts - lookback_minutes * 60

    all_results: list[dict] = []

    for promql in promql_queries:
        logger.info(f"[metrics] Executing PromQL: {promql}")
        try:
            # Try range query first
            resp = requests.get(
                f"{PROMETHEUS_URL}/api/v1/query_range",
                params={
                    "query": promql,
                    "start": str(start_ts),
                    "end": str(end_ts),
                    "step": str(step_seconds),
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") == "success":
                result_data = data.get("data", {}).get("result", [])
                all_results.append({
                    "query": promql,
                    "resultType": data.get("data", {}).get("resultType", "unknown"),
                    "result": result_data,
                })
                logger.info(
                    f"[metrics] PromQL '{promql}' returned {len(result_data)} series"
                )
            else:
                # Fallback to instant query
                resp2 = requests.get(
                    f"{PROMETHEUS_URL}/api/v1/query",
                    params={"query": promql, "time": str(end_ts)},
                    timeout=15,
                )
                resp2.raise_for_status()
                data2 = resp2.json()
                result_data2 = data2.get("data", {}).get("result", [])
                all_results.append({
                    "query": promql,
                    "resultType": data2.get("data", {}).get("resultType", "unknown"),
                    "result": result_data2,
                })

        except Exception as exc:
            logger.error(f"[metrics] PromQL '{promql}' failed: {exc}", exc_info=True)
            all_results.append({
                "query": promql,
                "error": str(exc),
            })

    has_any = any(r.get("result") for r in all_results if "error" not in r)
    has_error = any("error" in r for r in all_results)

    if not all_results:
        return {
            "raw_metrics": "[]",
            "fetch_error": "No PromQL queries were provided.",
            "has_results": False,
        }

    return {
        "raw_metrics": json.dumps(all_results, default=str),
        "fetch_error": "" if not has_error else "Some queries failed — partial results available.",
        "has_results": has_any,
    }


# NODE 3 – analyze_metrics (helpers)
# =================================

def _build_no_data_response(fetch_error: str = "", no_match: bool = False) -> dict:
    """Return a structured error/empty response when metrics are unavailable."""
    if fetch_error:
        return {
            "metrics_analysis": json.dumps({
                "summary": f"Could not fetch metrics: {fetch_error}",
                "current_values": {},
                "trends": [],
                "anomalies": [],
                "health_assessment": "unknown",
                "recommended_actions": [
                    "Check that Prometheus is running and reachable.",
                    "Verify scrape targets are configured correctly.",
                ],
            }),
        }
    return {
        "metrics_analysis": json.dumps({
            "summary": "No metric data was found for the given queries and time range.",
            "current_values": {},
            "trends": [],
            "anomalies": [],
            "health_assessment": "unknown",
            "recommended_actions": [
                "Try broadening the time range.",
                "Ensure the application is being scraped by Prometheus.",
            ],
        }),
    }


def _truncate_metrics(raw_metrics: str, max_chars: int = 12000) -> str:
    """Truncate raw metrics string to avoid exceeding the LLM context window."""
    if len(raw_metrics) > max_chars:
        return raw_metrics[:max_chars] + "\n... (truncated)"
    return raw_metrics


def _build_analysis_prompt(user_query: str, time_range_description: str, truncated: str) -> str:
    """Build the LLM prompt for metrics analysis."""
    return f"""You are a DevOps metrics-analysis assistant.

The user asked: "{user_query}"
Time range analysed: {time_range_description}

Below is the raw Prometheus query result data (JSON).
Analyse it and produce:
1. **summary** – concise executive summary of findings.
2. **current_values** – dict of metric name → latest value (human-readable).
3. **trends** – list of observed trends (increasing, decreasing, stable, spikes).
4. **anomalies** – any unexpected patterns or outlier values.
5. **health_assessment** – one of: "healthy", "degraded", "critical".
6. **recommended_actions** – suggestions based on the analysis.

Raw metrics data:
{truncated}"""


def _fallback_analysis(raw_metrics: str) -> dict:
    """Return a fallback analysis response when the LLM call fails."""
    try:
        data = json.loads(raw_metrics)
        query_count = len(data)
        total_series = sum(len(r.get("result", [])) for r in data if "error" not in r)
    except Exception:
        query_count = 0
        total_series = 0
    return {
        "metrics_analysis": json.dumps({
            "summary": (
                f"Executed {query_count} queries with {total_series} result series. "
                "LLM analysis unavailable — showing raw counts."
            ),
            "current_values": {},
            "trends": [],
            "anomalies": [],
            "health_assessment": "unknown",
            "recommended_actions": [],
        }),
    }


def analyze_metrics(state: MetricsRequestGraphState):
    """Use the LLM to analyse the raw Prometheus query results."""

    raw_metrics = state.get("raw_metrics", "[]")
    has_results = state.get("has_results", False)
    fetch_error = state.get("fetch_error", "")
    user_query = state["user_query"]
    time_range_description = state.get("time_range_description", "")

    if fetch_error and not has_results:
        logger.warning(f"[metrics] Skipping analysis – fetch error: {fetch_error}")
        return _build_no_data_response(fetch_error=fetch_error)

    if not has_results:
        logger.info("[metrics] No metric data matched the queries.")
        return _build_no_data_response(no_match=True)

    truncated = _truncate_metrics(raw_metrics)
    prompt = _build_analysis_prompt(user_query, time_range_description, truncated)

    try:
        logger.info("[metrics] Analysing metrics data with LLM...")
        result = metrics_analysis_llm.invoke(prompt)
        logger.info(f"[metrics] Analysis complete: {result}")
        return {"metrics_analysis": result.model_dump_json()}
    except Exception as exc:
        logger.error(f"[metrics] analyze_metrics failed: {exc}", exc_info=True)
        return _fallback_analysis(raw_metrics)
    

    
# NODE 4 – format_metrics_response
# =================================

def format_metrics_response(state: MetricsRequestGraphState, config: RunnableConfig):
    """Turn the structured analysis into a polished markdown response."""

    analysis_raw = state.get("metrics_analysis", "{}")
    user_query = state["user_query"]
    has_results = state.get("has_results", False)

    try:
        analysis = json.loads(analysis_raw)
    except json.JSONDecodeError:
        analysis = {"summary": analysis_raw}

    # If no data matched, just output a simple polite text
    if not has_results:
        summary = analysis.get("summary", "No metric data matched your query.")
        recs = "\\n- ".join(analysis.get("recommended_actions", []))
        if recs:
            summary += f"\\n\\n**Suggestions**:\\n- {recs}"
        return {
            "formatted_response": summary,
            "messages": [{"role": "assistant", "content": summary}],
        }

    prompt = f"""You are a professional DevOps assistant.

The user asked: "{user_query}"

Here is the structured metrics analysis:
{json.dumps(analysis, indent=2)}

Format a clear, user-friendly response following these rules:
- Start with a one-line **summary**.
- Present **current values** in a clean table or list.
- Describe **trends** as bullet points.
- Highlight any **anomalies** prominently.
- Show the **health assessment** with an appropriate emoji (✅ healthy, ⚠️ degraded, 🔴 critical).
- End with **recommended actions** as numbered steps.
- Use markdown formatting for readability.
- Do NOT expose raw JSON, PromQL, or internal system details.
- If no data was found, say so clearly.

Respond ONLY with the formatted answer — no preamble."""

    try:
        logger.info("[metrics] Formatting metrics analysis response...")
        llm_response = base_llm.invoke(prompt, config=config)
        formatted = llm_response.content
        logger.info("[metrics] Formatted response generated.")
    except Exception:
        formatted = analysis.get("summary", "Metrics analysis complete.")

    return {
        "formatted_response": formatted,
        "messages": [{"role": "assistant", "content": formatted}],
    }
