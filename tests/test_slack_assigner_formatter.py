from __future__ import annotations

import json

from slack_integration import slack_formatter, smart_assigner


def test_parse_business_envelope_accepts_raw_and_fenced_json():
    payload = {"status": "success", "result": {"summary": "ok"}}

    assert smart_assigner.parse_business_envelope(json.dumps(payload)) == payload
    assert smart_assigner.parse_business_envelope(
        "```json\n" + json.dumps(payload) + "\n```"
    ) == payload


def test_parse_business_envelope_rejects_markdown_and_bad_json():
    assert smart_assigner.parse_business_envelope("plain text") is None
    assert smart_assigner.parse_business_envelope("{bad json") is None


def test_extract_risk_and_summary_supports_nested_envelope():
    envelope = {"result": {"risk_level": "high", "summary": "cash is tight"}}

    assert smart_assigner.extract_risk_and_summary(envelope, "fallback") == (
        "high",
        "cash is tight",
    )


def test_extract_risk_and_summary_falls_back_to_text():
    risk, summary = smart_assigner.extract_risk_and_summary(None, "x" * 9000)

    assert risk is None
    assert summary == "x" * 8000


def test_should_notify_assignee_for_high_risk_critical_or_explicit_escalation():
    assert smart_assigner.should_notify_assignee(
        user_query="review this", risk_level="HIGH", summary="normal"
    )
    assert smart_assigner.should_notify_assignee(
        user_query="review this", risk_level="low", summary="possible bankruptcy risk"
    )
    assert smart_assigner.should_notify_assignee(
        user_query="please assign this", risk_level=None, summary="normal"
    )
    assert not smart_assigner.should_notify_assignee(
        user_query="review this", risk_level="low", summary="normal"
    )


def test_pick_assignee_slack_id_prefers_matching_env_over_default(monkeypatch):
    monkeypatch.setenv("SLACK_ID_DEFAULT", "UDEFAULT")
    monkeypatch.setenv("SLACK_ID_MARKETING", "UMARKETING")
    monkeypatch.setenv("SLACK_ID_BACKEND", "UBACKEND")

    assert (
        smart_assigner.pick_assignee_slack_id(
            user_query="marketing campaign spend", summary=""
        )
        == "UMARKETING"
    )
    assert (
        smart_assigner.pick_assignee_slack_id(
            user_query="database api timeout", summary=""
        )
        == "UBACKEND"
    )
    assert smart_assigner.pick_assignee_slack_id(user_query="other", summary="") == "UDEFAULT"


def test_slack_thread_id_uses_unknown_defaults():
    assert smart_assigner.slack_thread_id("", "U1") == "slack_unknown_U1"
    assert smart_assigner.slack_thread_id("T1", "") == "slack_T1_unknown"


def test_followup_encode_decode_round_trip_and_invalid_value():
    value = slack_formatter._encode_followup_value("thread-1", "What about revenue?")

    assert slack_formatter.decode_followup_value(value) == (
        "thread-1",
        "What about revenue?",
    )
    assert slack_formatter.decode_followup_value("not-valid-base64") is None


def test_build_reply_blocks_from_envelope_includes_context_and_followups():
    envelope = {
        "query_understood": "monthly revenue",
        "result": {
            "summary": "Revenue improved.",
            "recommendations": ["Track margin"],
            "risk_level": "low",
        },
        "follow_up_questions": ["Compare to last month?", "Show top products?"],
    }

    blocks = slack_formatter.build_reply_blocks(
        json.dumps(envelope),
        thread_id="thread-1",
        intent_str="database_request",
    )

    assert blocks[0]["type"] == "section"
    assert any(block["type"] == "context" for block in blocks)
    action_block = next(block for block in blocks if block["type"] == "actions")
    assert len(action_block["elements"]) == 2
    decoded = slack_formatter.decode_followup_value(action_block["elements"][0]["value"])
    assert decoded == ("thread-1", "Compare to last month?")


def test_build_reply_blocks_splits_long_plain_text_and_uses_empty_fallback():
    long_blocks = slack_formatter.build_reply_blocks(
        "x" * 3100, thread_id="thread-1"
    )
    assert [block["type"] for block in long_blocks] == ["section", "section"]

    empty_blocks = slack_formatter.build_reply_blocks("", thread_id="thread-1")
    assert empty_blocks[0]["type"] == "section"
    assert "could not produce a reply" in empty_blocks[0]["text"]["text"]
