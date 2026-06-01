"""
Node functions for the Logs-Request LangGraph subgraph.

Graph flow:
  parse_logs_query  ->  fetch_logs  ->  analyze_logs  ->  format_logs_response

Data source: Grafana Loki HTTP API (same Loki that Promtail ships our app.log to).
Loki label used by Promtail:  job="python_app"
"""

import json
import os
import requests
import time
from datetime import date
from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig

from llm.base_llm import base_llm
from logger.logger import logger
from intents.logs_request_graph.graph_state import LogsRequestGraphState
from intents.logs_request_graph.structures import (
    LogsQueryParseOutput,
    LogsAnalysisOutput,
)

load_dotenv()

# Loki connection (Promtail pushes to this same instance)
LOKI_URL = os.getenv("LOKI_URL", "http://loki:3100")
LOKI_REQUEST_TIMEOUT = (5, 20)  # connect timeout, read timeout

# LLMs with structured output
logs_query_parse_llm = base_llm.with_structured_output(LogsQueryParseOutput)
logs_analysis_llm = base_llm.with_structured_output(LogsAnalysisOutput)


# ── NODE 1 – parse_logs_query ──────────────────────────────────────────
def parse_logs_query(state: LogsRequestGraphState):
    """Use the LLM to derive a Loki LogQL query from the user's natural-language request."""

    user_query = state["user_query"]
    today_str = date.today().isoformat()

    logger.info(f"[logs] Parsing logs query: '{user_query}'")

    prompt = f"""You are a Loki log-query assistant for an intelligent business agent application.
Today's date is {today_str}.

The application logs are shipped to Loki by Promtail with the label:  job="python_app"
Log lines follow this format:
  YYYY-MM-DD HH:MM:SS - <logger_name> - <LEVEL> - <filename>:<lineno> - <function> - <message>

Log levels present: INFO, WARNING, ERROR, CRITICAL

Modules / subsystems visible in logs:
- intent_detection   – classifying user intent
- database_request   – SQL generation and DB queries
- logs_request       – log fetching and analysis
- metrics_request    – Prometheus metric queries
- general_information_graph – general Q&A
- format_response    – response formatting
- app                – Flask routing / API layer

Based on the user's query, produce:

1. **log_query** – a valid Loki LogQL expression.
   - Always start with the stream selector: {{job="python_app"}}
   - Add pipeline stages as needed:
       |= "keyword"          (exact match)
       |~ "regex"            (regex match)
       != "exclude"          (exclude lines)
       | logfmt              (parse structured log fields)
   - For error/warning queries:  {{job="python_app"}} |= "ERROR"
   - For module-specific queries: {{job="python_app"}} |= "intent_detection"
   - For a specific function/event: {{job="python_app"}} |= "handle_database_request"
   - If vague ("show me logs"), use:  {{job="python_app"}}

2. **lookback_minutes** – how far back to fetch:
     "last 5 minutes"  -> 5
     "last hour"       -> 60
     "last 24 hours"   -> 1440
     Default 60 if unspecified.

3. **limit** – max log lines to return (default 100, max 500).

4. **time_range_description** – human-readable time range.

5. **search_keywords** – key terms extracted from the query (list of strings).

User Query: {user_query}"""

    try:
        result = logs_query_parse_llm.invoke(prompt)
        logger.info(f"[logs] Parsed logs query: {result}")
        return {
            "log_query": result.log_query,
            "lookback_minutes": result.lookback_minutes,
            "limit": result.limit,
            "time_range_description": result.time_range_description,
            "search_keywords": result.search_keywords,
        }
    except Exception as exc:
        logger.error(f"[logs] parse_logs_query failed: {exc}", exc_info=True)
        # Sensible defaults – broad recent logs
        return {
            "log_query": '{job="python_app"}',
            "lookback_minutes": 60,
            "limit": 100,
            "time_range_description": "Last 60 minutes (default – could not parse query)",
            "search_keywords": [],
        }


# ── NODE 2 – fetch_logs (Loki HTTP API) ───────────────────────────────
def fetch_logs(state: LogsRequestGraphState):
    """Execute the LogQL query against the Loki HTTP API and collect plain-text log lines."""

    log_query = state.get("log_query", '{job="python_app"}')
    lookback_minutes = state.get("lookback_minutes", 60)
    limit = state.get("limit", 100)

    # Loki expects nanosecond Unix timestamps as strings
    end_ns = int(time.time() * 1e9)
    start_ns = int((time.time() - lookback_minutes * 60) * 1e9)

    logger.info(
        f"[logs] Fetching logs with query='{log_query}' "
        f"lookback={lookback_minutes}m limit={limit}"
    )

    try:
        resp = requests.get(
            f"{LOKI_URL}/loki/api/v1/query_range",
            params={
                "query": log_query,
                "start": str(start_ns),
                "end": str(end_ns),
                "limit": str(limit),
                "direction": "backward",   # newest first
            },
            timeout=LOKI_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "success":
            error_msg = data.get("error", "Loki returned a non-success status.")
            logger.warning(f"[logs] Loki query failed: {error_msg}")
            return {
                "raw_logs": "",
                "fetch_error": error_msg,
                "has_results": False,
                "log_line_count": 0,
            }

        # Loki returns streams: each stream has a list of [timestamp, line] pairs
        streams = data.get("data", {}).get("result", [])
        lines: list[str] = []
        for stream in streams:
            for ts, line in stream.get("values", []):
                lines.append(line)

        # Re-sort chronologically (oldest first) for better LLM readability
        lines.reverse()

        log_line_count = len(lines)
        raw_logs = "\n".join(lines) if lines else ""

        logger.info(f"[logs] Fetched {log_line_count} log lines from Loki.")
        return {
            "raw_logs": raw_logs,
            "fetch_error": "",
            "has_results": log_line_count > 0,
            "log_line_count": log_line_count,
        }

    except requests.exceptions.Timeout:
        error_msg = (
            f"Timed out fetching logs from Loki at {LOKI_URL} "
            f"after connect/read timeouts {LOKI_REQUEST_TIMEOUT}."
        )
        logger.error(f"[logs] {error_msg}", exc_info=True)
        return {
            "raw_logs": "",
            "fetch_error": error_msg,
            "has_results": False,
            "log_line_count": 0,
        }
    except requests.exceptions.ConnectionError:
        error_msg = f"Cannot connect to Loki at {LOKI_URL}. Is Loki running?"
        logger.error(f"[logs] {error_msg}", exc_info=True)
        return {
            "raw_logs": "",
            "fetch_error": error_msg,
            "has_results": False,
            "log_line_count": 0,
        }
    except Exception as exc:
        logger.error(f"[logs] fetch_logs failed: {exc}", exc_info=True)
        return {
            "raw_logs": "",
            "fetch_error": str(exc),
            "has_results": False,
            "log_line_count": 0,
        }


# ── NODE 3 – analyze_logs ──────────────────────────────────────────────
def analyze_logs(state: LogsRequestGraphState):
    """Use the LLM to analyse the retrieved log lines and produce structured insights."""

    raw_logs = state.get("raw_logs", "")
    has_results = state.get("has_results", False)
    fetch_error = state.get("fetch_error", "")
    user_query = state["user_query"]
    time_range_description = state.get("time_range_description", "")
    log_line_count = state.get("log_line_count", 0)

    if fetch_error and not has_results:
        logger.warning(f"[logs] Skipping analysis – fetch error: {fetch_error}")
        return {
            "logs_analysis": json.dumps({
                "summary": f"Could not fetch logs: {fetch_error}",
                "error_count": 0,
                "warning_count": 0,
                "key_events": [],
                "recurring_patterns": [],
                "anomalies": [],
                "health_assessment": "unknown",
                "recommended_actions": [
                    "Check that Loki is running and reachable.",
                    "Verify that Promtail is configured to ship logs to Loki.",
                ],
            }),
        }

    if not has_results:
        logger.info("[logs] No log lines matched the query.")
        return {
            "logs_analysis": json.dumps({
                "summary": "No log lines were found for the given query and time range.",
                "error_count": 0,
                "warning_count": 0,
                "key_events": [],
                "recurring_patterns": [],
                "anomalies": [],
                "health_assessment": "unknown",
                "recommended_actions": [
                    "Try broadening the time range.",
                    "Check that the application is running and generating logs.",
                    "Verify Promtail is shipping logs to Loki.",
                ],
            }),
        }

    # Truncate to stay within LLM context window
    max_chars = 12_000
    truncated = raw_logs[:max_chars]
    if len(raw_logs) > max_chars:
        truncated += "\n... (truncated for analysis)"

    prompt = f"""You are a DevOps log-analysis assistant for a Python Flask / LangGraph intelligent business agent.

The user asked: "{user_query}"
Time range analysed: {time_range_description}
Total log lines retrieved: {log_line_count}

Log line format:
  YYYY-MM-DD HH:MM:SS - <logger> - <LEVEL> - <filename>:<lineno> - <function> - <message>

Analyse the log lines below and produce:
1. **summary** – concise executive summary of what is happening.
2. **error_count** – exact count of ERROR-level lines.
3. **warning_count** – exact count of WARNING-level lines.
4. **key_events** – list of the most important individual events (up to 10 short descriptions).
5. **recurring_patterns** – patterns that repeat frequently (e.g., "repeated DB connection errors").
6. **anomalies** – unexpected or suspicious entries worth investigating.
7. **health_assessment** – one of: "healthy", "degraded", "critical".
8. **recommended_actions** – concrete next steps based on the findings.

Log lines:
{truncated}"""

    try:
        logger.info("[logs] Analysing log lines with LLM...")
        result = logs_analysis_llm.invoke(prompt)
        logger.info(f"[logs] Analysis complete: {result}")
        return {"logs_analysis": result.model_dump_json()}
    except Exception as exc:
        logger.error(f"[logs] analyze_logs failed: {exc}", exc_info=True)
        # Fallback – count levels manually
        error_count = raw_logs.count(" - ERROR - ")
        warning_count = raw_logs.count(" - WARNING - ")
        return {
            "logs_analysis": json.dumps({
                "summary": (
                    f"Retrieved {log_line_count} log lines. "
                    f"Found {error_count} ERRORs and {warning_count} WARNINGs. "
                    "LLM analysis unavailable — showing raw counts."
                ),
                "error_count": error_count,
                "warning_count": warning_count,
                "key_events": [],
                "recurring_patterns": [],
                "anomalies": [],
                "health_assessment": "critical" if error_count > 0 else "healthy",
                "recommended_actions": [],
            }),
        }


# ── NODE 4 – format_logs_response ─────────────────────────────────────
def format_logs_response(state: LogsRequestGraphState, config: RunnableConfig):
    """Turn the structured log analysis into a polished markdown response."""

    analysis_raw = state.get("logs_analysis", "{}")
    user_query = state["user_query"]
    time_range_description = state.get("time_range_description", "")
    log_line_count = state.get("log_line_count", 0)
    has_results = state.get("has_results", False)

    try:
        analysis = json.loads(analysis_raw)
    except json.JSONDecodeError:
        analysis = {"summary": analysis_raw}

    # Early exit if no logs generated
    if not has_results:
        summary = analysis.get("summary", "No logs matched your query.")
        recs = "\\n- ".join(analysis.get("recommended_actions", []))
        if recs:
            summary += f"\\n\\n**Suggestions**:\\n- {recs}"
        return {
            "formatted_response": summary,
            "messages": [{"role": "assistant", "content": summary}],
        }

    prompt = f"""You are a professional DevOps assistant.

The user asked: "{user_query}"
Time range: {time_range_description}
Log lines analysed: {log_line_count}

Here is the structured log analysis:
{json.dumps(analysis, indent=2)}

Format a clear, user-friendly response following these rules:
- Start with a one-line **summary**.
- Show **error/warning counts** prominently.
- List the **key events** as concise bullet points.
- Highlight any **anomalies** in a warning block.
- Show the **health assessment** with an appropriate emoji (✅ healthy, ⚠️ degraded, 🔴 critical).
- End with **recommended actions** as numbered steps.
- Use markdown formatting for readability.
- Do NOT expose internal LogQL queries or system implementation details.
- If no logs were found, say so clearly and suggest next steps.

Respond ONLY with the formatted answer — no preamble."""

    try:
        logger.info("[logs] Formatting log analysis response...")
        llm_response = base_llm.invoke(prompt, config=config)
        formatted = llm_response.content
        logger.info("[logs] Formatted response generated.")
    except Exception:
        formatted = analysis.get("summary", "Log analysis complete.")

    return {
        "formatted_response": formatted,
        "messages": [{"role": "assistant", "content": formatted}],
    }
