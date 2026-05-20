"""Structured debug logging for LangGraph / Flask agent flows."""
from __future__ import annotations

import time
from datetime import datetime, timezone

from logger.logger import logger


def safe_state_summary(state: dict) -> dict:
    """Compact state for logs (no large blobs)."""
    su = state.get("status_updates")
    return {
        "user_query": (state.get("user_query") or "")[:80],
        "intent": state.get("intent", "unknown"),
        "route": state.get("route", "unknown"),
        "step_count": state.get("step_count", 0),
        "sql_retry_count": state.get("sql_retry_count", 0),
        "is_sql_valid": state.get("is_sql_valid"),
        "error_message": (state.get("error_message") or "")[:200],
        "status_updates_len": len(su) if isinstance(su, list) else 0,
        "high_level_intent": state.get("high_level_intent"),
    }


def log_node_enter(node_name: str, state: dict, message: str | None = None) -> float:
    """Log node start; returns t0 for log_node_exit."""
    msg = message or f"Entering {node_name}"
    logger.info(
        "[→ ENTER] %s | step=%s | intent=%s | query=%r",
        node_name,
        state.get("step_count", 0),
        state.get("intent") or state.get("high_level_intent") or "unknown",
        (state.get("user_query") or "")[:50],
    )
    logger.info("[NODE_ENTER] %s: %s", node_name, msg)
    return time.perf_counter()


def log_node_exit(node_name: str, state: dict, t0: float, route_key: str = "route") -> None:
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    logger.info(
        "[← EXIT] %s | route=%s | duration_ms=%s",
        node_name,
        state.get(route_key, "unknown"),
        elapsed_ms,
    )


def log_route(from_node: str, to_node: str, reason: str) -> None:
    logger.info("[⚡ ROUTE] %s → %s | reason=%r", from_node, to_node, reason[:120])


def log_error(node_name: str, exc: BaseException, state: dict) -> None:
    logger.error(
        "[✗ ERROR] %s | error=%r | state_snapshot=%s",
        node_name,
        str(exc),
        safe_state_summary(state),
        exc_info=True,
    )


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
