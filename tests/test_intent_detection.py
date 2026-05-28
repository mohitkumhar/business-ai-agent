from __future__ import annotations

import pytest

from agent_code.nodes import intent_detection


def test_normalize_labels_maps_legacy_names():
    assert intent_detection._normalize_labels(
        ["greeting", "out_of_scope", "database_request"]
    ) == ["greeting_request", "out_of_scope_request", "database_request"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("hello!", ["greeting_request"]),
        ("tell me a joke", ["out_of_scope_request"]),
        ("show me the stack trace from the checkout error", ["logs_request"]),
        ("what is the api latency p95 for the server?", ["metrics_request"]),
        ("can I afford a loan if revenue drops 20%?", ["hybrid_request"]),
        ("how much revenue did I have last month?", ["database_request"]),
        ("should I spend more on marketing?", ["advisory_request"]),
    ],
)
def test_fast_intent_common_paths(text, expected):
    assert intent_detection._fast_intent(text) == {"intent": expected}


def test_fast_intent_orders_compound_database_then_advisory():
    result = intent_detection._fast_intent(
        "How much revenue did I make last month and should I increase marketing?"
    )

    assert result == {"intent": ["database_request", "advisory_request"]}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", False),
        ("hello", True),
        ("hey can you show revenue last month", False),
        ("good morning, should I hire?", False),
    ],
)
def test_looks_like_pure_greeting(text, expected):
    assert intent_detection._looks_like_pure_greeting(text) is expected


def test_order_intents_deduplicates_sorts_and_drops_stray_greeting():
    result = intent_detection.order_intents_for_execution(
        [
            "advisory_request",
            "greeting_request",
            "database_request",
            "database_request",
            "metrics_request",
        ]
    )

    assert result == ["database_request", "metrics_request", "advisory_request"]


def test_order_intents_drops_out_of_scope_when_compound_has_supported_work():
    result = intent_detection.order_intents_for_execution(
        ["out_of_scope_request", "general_information_request"]
    )

    assert result == ["general_information_request"]


def test_order_intents_defaults_empty_to_general_information():
    assert intent_detection.order_intents_for_execution([]) == [
        "general_information_request"
    ]


def test_order_intents_caps_chain_length():
    result = intent_detection.order_intents_for_execution(
        [
            "metrics_request",
            "logs_request",
            "database_request",
            "general_information_request",
            "hybrid_request",
            "advisory_request",
        ]
    )

    assert result == [
        "metrics_request",
        "logs_request",
        "database_request",
        "general_information_request",
    ]


@pytest.mark.parametrize(
    ("primary", "expected"),
    [
        ("out_of_scope_request", "out_of_scope"),
        ("advisory_request", "advisory"),
        ("hybrid_request", "hybrid"),
        ("database_request", "database"),
        ("general_information_request", "database"),
    ],
)
def test_map_app_intent_to_high_level(primary, expected):
    assert intent_detection.map_app_intent_to_high_level(primary) == expected
