from __future__ import annotations

from agent_code.intents.database_request_graph import step_utils


def test_step_guard_increments_without_halting_below_limit():
    assert step_utils.step_guard({"step_count": 1, "max_steps": 3}) == {
        "step_count": 2
    }


def test_step_guard_sets_halt_when_limit_reached():
    result = step_utils.step_guard({"step_count": 2, "max_steps": 3})

    assert result["step_count"] == 3
    assert result["halt_pipeline"] is True
    assert result["emergency_reason"] == "max_steps_exceeded"


def test_step_guard_exempts_terminal_nodes_from_halt():
    result = step_utils.step_guard(
        {"step_count": 99, "max_steps": 3},
        current_node="standardized_response_formatter",
    )

    assert result == {"step_count": 100}


def test_handle_step_guard_trigger_routes_to_formatter_when_data_exists():
    result = step_utils.handle_step_guard_trigger(
        {
            "query_results": [{"amount": 10}],
            "halt_pipeline": True,
            "emergency_reason": "max_steps_exceeded",
        },
        "business_insight_generator",
    )

    assert result["route"] == "format_response_of_business_insight_generator"
    assert result["halt_pipeline"] is False
    assert result["emergency_reason"] == ""


def test_handle_step_guard_trigger_routes_to_emergency_without_data():
    result = step_utils.handle_step_guard_trigger({"query_results": "[]"}, "SQL_generation")

    assert result["route"] == "emergency_exit"
    assert "unable to complete" in result["formatted_response"]


def test_wrap_node_skips_non_exempt_node_when_pipeline_already_halted():
    def node(state):
        raise AssertionError("node should not be called")

    wrapped = step_utils.wrap_node(node)

    assert wrapped({"halt_pipeline": True}) == {}


def test_wrap_node_merges_step_guard_and_node_output():
    def node(state):
        return {"value": state["step_count"] + 10}

    wrapped = step_utils.wrap_node(node)

    assert wrapped({"step_count": 0, "max_steps": 5}) == {
        "step_count": 1,
        "value": 11,
    }


def test_wrap_node_passes_config_when_function_accepts_it():
    def node(state, config):
        return {"has_config": bool(config)}

    wrapped = step_utils.wrap_node(node)

    assert wrapped({"step_count": 0, "max_steps": 5}) == {
        "step_count": 1,
        "has_config": True,
    }


def test_route_emergency_or_prefers_emergency_when_halted_or_reason_present():
    route = step_utils.route_emergency_or("next_node")

    assert route({"halt_pipeline": True}) == "emergency_exit"
    assert route({"emergency_reason": "max_steps_exceeded"}) == "emergency_exit"
    assert route({}) == "next_node"
