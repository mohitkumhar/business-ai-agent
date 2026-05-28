"""Step budget for LangGraph nodes — prevents runaway loops."""
import inspect
from typing import Any, Callable

from logger.logger import logger

MAX_STEPS_DEFAULT = 16  # BUG2 FIX: was 12 — too low to allow format_response to run

# BUG2 FIX: terminal nodes must never be blocked by the step guard
EXEMPT_FROM_STEP_GUARD: set[str] = {
    "format_response_of_business_insight_generator",
    "standardized_response_formatter",
    "emergency_exit",
    "logging",
}


def step_guard(state: dict, current_node: str = "") -> dict:
    """Increment step_count; set halt_pipeline when max_steps reached.

    Terminal nodes listed in EXEMPT_FROM_STEP_GUARD are never halted.
    """
    # BUG2 FIX: exempt terminal nodes so format_response always runs
    if current_node in EXEMPT_FROM_STEP_GUARD:
        logger.debug("[STEP GUARD] Exempting terminal node: %s", current_node)
        n = int(state.get("step_count") or 0) + 1
        return {"step_count": n}

    n = int(state.get("step_count") or 0) + 1
    m = int(state.get("max_steps") or MAX_STEPS_DEFAULT)
    out: dict[str, Any] = {"step_count": n}
    if n >= m:
        out["halt_pipeline"] = True
        out["emergency_reason"] = "max_steps_exceeded"
        logger.warning("Step limit reached (%s >= %s), halting pipeline", n, m)
    return out


def handle_step_guard_trigger(state: dict, current_node: str) -> dict:
    """BUG2 FIX: if step guard fires but data was already fetched, route to
    format_response instead of dead-ending at emergency_exit."""
    has_data = bool(
        state.get("query_results")
        and state["query_results"] not in ("", "[]", "null")
    )
    if has_data:
        logger.info(
            "[STEP GUARD] Data exists at node '%s', routing to format_response anyway",
            current_node,
        )
        return {**state, "route": "format_response_of_business_insight_generator",
                "halt_pipeline": False, "emergency_reason": ""}
    return {
        **state,
        "route": "emergency_exit",
        "formatted_response": (
            "I was unable to complete processing your request. "
            "Please try rephrasing your question."
        ),
    }


def wrap_node(fn: Callable) -> Callable:
    """Run step_guard before node; on halt return early; merge step into result."""

    sig = inspect.signature(fn)
    has_config = "config" in sig.parameters
    node_name = fn.__name__

    def wrapped(state: dict, *args: Any, **kwargs: Any) -> dict:
        if state.get("halt_pipeline") and node_name not in EXEMPT_FROM_STEP_GUARD:
            return {}
        g = step_guard(state, current_node=node_name)
        if g.get("halt_pipeline"):
            # BUG2 FIX: don't hard-stop if data is already available
            return handle_step_guard_trigger({**state, **g}, node_name)
        merged = {**state, **g}
        if has_config:
            config = kwargs.get("config")
            if config is None and args:
                config = args[0]
            if config is None:
                config = {"configurable": {}}
            out = fn(merged, config)
        else:
            out = fn(merged)
        if not isinstance(out, dict):
            out = {}
        return {**g, **out}

    return wrapped


def route_emergency_or(next_label: str):
    """Factory for conditional edges: emergency_exit vs continue."""

    def _route(state: dict) -> str:
        if state.get("halt_pipeline") or state.get("emergency_reason"):
            return "emergency_exit"
        return next_label

    return _route
