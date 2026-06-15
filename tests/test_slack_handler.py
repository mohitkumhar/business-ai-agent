"""Regression tests for agent_code/slack_integration/slack_handler.py (issue #330)."""
from __future__ import annotations

import base64
import json
import sys
import types
from unittest.mock import MagicMock, patch

# slack_sdk is not in the CI pip list; stub it before importing slack_handler.
if "slack_sdk" not in sys.modules:
    _sdk = types.ModuleType("slack_sdk")
    _sdk_err = types.ModuleType("slack_sdk.errors")

    class _SlackApiError(Exception):  # noqa: N818
        def __init__(self, message="", response=None):
            super().__init__(message)
            self.response = response if response is not None else {}

    class _WebClient:
        def __init__(self, token="", **kwargs):
            self.token = token

    _sdk.WebClient = _WebClient
    _sdk_err.SlackApiError = _SlackApiError
    _sdk.errors = _sdk_err
    sys.modules["slack_sdk"] = _sdk
    sys.modules["slack_sdk.errors"] = _sdk_err

# query_execution has heavy transitive deps; stub the one symbol we need.
if "query_execution" not in sys.modules:
    _qe = types.ModuleType("query_execution")
    _qe.stream_agent_sse_lines = lambda *a, **kw: iter([])
    sys.modules["query_execution"] = _qe

from slack_integration.slack_handler import (  # noqa: E402
    SlackDelivery,
    _event_from_sse_chunk,
    _safe_ephemeral_or_dm,
    _truncate_block,
    handle_follow_up_interaction,
    handle_slack_message_event,
    strip_slack_mentions,
)

SlackApiError = sys.modules["slack_sdk.errors"].SlackApiError


def _sse(event_type: str, **kwargs) -> str:
    return f"data: {json.dumps({'type': event_type, **kwargs})}\n"


def _mock_delivery(demo_channel: str = "CDEMO") -> tuple[SlackDelivery, MagicMock]:
    # Bypass __init__ to avoid env-var lookup and WebClient instantiation.
    d = SlackDelivery.__new__(SlackDelivery)
    mock_client = MagicMock()
    d._client = mock_client
    d.demo_channel_id = demo_channel
    return d, mock_client


def _encode(thread_id: str, question: str) -> str:
    from slack_integration.slack_formatter import _encode_followup_value
    return _encode_followup_value(thread_id, question)


class TestStripSlackMentions:
    def test_removes_single_mention_prefix(self):
        assert strip_slack_mentions("<@U12345> hello") == "hello"

    def test_removes_multiple_consecutive_mentions(self):
        assert strip_slack_mentions("<@U1> <@U2> what is revenue?") == "what is revenue?"

    def test_passthrough_when_no_mention_present(self):
        assert strip_slack_mentions("plain message") == "plain message"

    def test_mention_only_returns_empty_string(self):
        assert strip_slack_mentions("<@UBOT>") == ""

    def test_empty_string_is_safe(self):
        assert strip_slack_mentions("") == ""

    def test_none_is_treated_as_empty(self):
        assert strip_slack_mentions(None) == ""


class TestEventFromSseChunk:
    def test_valid_data_line_returns_parsed_dict(self):
        assert _event_from_sse_chunk(_sse("token", content="hello")) == {"type": "token", "content": "hello"}

    def test_non_data_lines_return_none(self):
        assert _event_from_sse_chunk("event: message\nretry: 3000\n") is None

    def test_empty_chunk_returns_none(self):
        assert _event_from_sse_chunk("") is None

    def test_invalid_json_payload_returns_none(self):
        assert _event_from_sse_chunk("data: {not valid json}\n") is None

    def test_empty_data_payload_is_skipped(self):
        assert _event_from_sse_chunk("data:   \n") is None

    def test_multiline_chunk_picks_first_data_line(self):
        chunk = 'id: 1\ndata: {"type": "final", "intent_str": "db"}\n'
        assert _event_from_sse_chunk(chunk) == {"type": "final", "intent_str": "db"}

    def test_invalid_first_data_line_returns_none_without_fallthrough(self):
        chunk = "data: bad\ndata: " + json.dumps({"type": "token", "content": "ok"}) + "\n"
        assert _event_from_sse_chunk(chunk) is None


class TestTruncateBlock:
    def test_short_string_is_unchanged(self):
        assert _truncate_block("hello", 10) == "hello"

    def test_empty_string_is_unchanged(self):
        assert _truncate_block("", 5) == ""

    def test_none_is_treated_as_empty(self):
        assert _truncate_block(None, 5) == ""

    def test_string_exactly_at_limit_is_unchanged(self):
        assert _truncate_block("abcde", 5) == "abcde"

    def test_string_over_limit_ends_with_ellipsis(self):
        result = _truncate_block("abcdef", 5)
        assert result.endswith("…")
        assert len(result) == 5


class TestSlackDeliveryInit:
    def test_configured_true_when_token_present(self, monkeypatch):
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-real-token")
        monkeypatch.setenv("SLACK_DEMO_CHANNEL_ID", "CDEMO")
        d = SlackDelivery()
        assert d.configured() is True
        assert d.demo_channel_id == "CDEMO"

    def test_configured_false_when_no_token(self, monkeypatch):
        monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
        d = SlackDelivery()
        assert d.configured() is False
        assert d._client is None

    def test_whitespace_only_token_treated_as_missing(self, monkeypatch):
        monkeypatch.setenv("SLACK_BOT_TOKEN", "   ")
        d = SlackDelivery()
        assert d.configured() is False

    def test_demo_channel_id_defaults_to_empty_string(self, monkeypatch):
        monkeypatch.delenv("SLACK_DEMO_CHANNEL_ID", raising=False)
        monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
        d = SlackDelivery()
        assert d.demo_channel_id == ""

    def test_client_property_returns_same_object_as_private_attr(self, monkeypatch):
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
        d = SlackDelivery()
        assert d.client is d._client


class TestRunAgentTurn:
    def _d(self):
        d, _ = _mock_delivery()
        return d

    def _run(self, chunks, **kwargs):
        with patch("slack_integration.slack_handler.stream_agent_sse_lines", return_value=iter(chunks)):
            return self._d().run_agent_turn("q", "tid", **kwargs)

    def test_token_events_are_concatenated_into_message_text(self):
        result = self._run([_sse("token", content="Hello"), _sse("token", content=" World")])
        assert result == {"kind": "message", "text": "Hello World", "intent_str": ""}

    def test_final_event_captures_intent_str(self):
        result = self._run([_sse("token", content="ok"), _sse("final", intent_str="db_request")])
        assert result["kind"] == "message"
        assert result["intent_str"] == "db_request"

    def test_final_event_preserves_prior_intent_when_new_intent_is_empty(self):
        result = self._run([_sse("final", intent_str="database_request"), _sse("final", intent_str="")])
        assert result["intent_str"] == "database_request"

    def test_clarification_event_returns_early_with_correct_fields(self):
        result = self._run([_sse("clarification", clarification="Please clarify.", intent_str="gen")])
        assert result == {"kind": "clarification", "text": "Please clarify.", "intent_str": "gen"}

    def test_error_event_returns_error_kind_with_text(self):
        result = self._run([_sse("error", error="Timeout", intent_str="")])
        assert result["kind"] == "error"
        assert result["text"] == "Timeout"

    def test_empty_stream_returns_empty_message(self):
        assert self._run([]) == {"kind": "message", "text": "", "intent_str": ""}

    def test_unknown_event_types_are_silently_ignored(self):
        assert self._run([_sse("ping"), _sse("token", content="answer")])["text"] == "answer"

    def test_invalid_sse_chunk_without_data_prefix_is_skipped(self):
        assert self._run(["not-a-data-line\n", _sse("token", content="ok")])["text"] == "ok"

    def test_business_id_is_forwarded_to_stream_agent(self):
        with patch("slack_integration.slack_handler.stream_agent_sse_lines", return_value=iter([])) as m:
            self._d().run_agent_turn("q", "tid", business_id="BIZ42")
        m.assert_called_once_with("q", "tid", "BIZ42")


class TestOpenDmChannel:
    def test_returns_channel_id_on_success(self):
        d, mock_client = _mock_delivery()
        mock_client.conversations_open.return_value = {"channel": {"id": "DDIRECT"}}
        assert d._open_dm_channel("UUSER") == "DDIRECT"
        mock_client.conversations_open.assert_called_once_with(users="UUSER")

    def test_returns_none_on_slack_api_error(self):
        d, mock_client = _mock_delivery()
        mock_client.conversations_open.side_effect = SlackApiError("not_allowed", response={})
        assert d._open_dm_channel("UUSER") is None

    def test_returns_none_when_response_missing_channel_key(self):
        d, mock_client = _mock_delivery()
        mock_client.conversations_open.return_value = {}
        assert d._open_dm_channel("UUSER") is None

    def test_returns_none_on_type_error(self):
        d, mock_client = _mock_delivery()
        mock_client.conversations_open.side_effect = TypeError("unexpected NoneType")
        assert d._open_dm_channel("UUSER") is None


def _deliver(delivery, *, try_channel=None, with_hdr=False, text="Hi!", user_id="UUSER"):
    delivery.deliver_assistant_reply(
        slack_user_id=user_id,
        assistant_text=text,
        intent_str="",
        graph_thread_id="tid",
        user_query_for_context="what is revenue?",
        try_channel_id_first=try_channel,
        with_user_context_header=with_hdr,
    )


class TestDeliverAssistantReply:
    def test_no_client_returns_without_api_calls(self, monkeypatch):
        monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
        _deliver(SlackDelivery())

    def test_posts_to_channel_when_try_channel_provided(self):
        d, mock_client = _mock_delivery("CDEMO")
        _deliver(d, try_channel="CDEMO")
        mock_client.chat_postMessage.assert_called_once()
        assert mock_client.chat_postMessage.call_args.kwargs["channel"] == "CDEMO"

    def test_falls_back_to_dm_on_known_channel_error(self):
        d, mock_client = _mock_delivery("CDEMO")
        mock_client.chat_postMessage.side_effect = [
            SlackApiError("not_in_channel", response={"error": "not_in_channel"}),
            None,
        ]
        mock_client.conversations_open.return_value = {"channel": {"id": "DM_CH"}}
        _deliver(d, try_channel="CDEMO")
        assert mock_client.chat_postMessage.call_count == 2
        assert mock_client.chat_postMessage.call_args_list[1].kwargs["channel"] == "DM_CH"

    def test_unexpected_channel_error_also_falls_back_to_dm(self):
        d, mock_client = _mock_delivery("CDEMO")
        mock_client.chat_postMessage.side_effect = [
            SlackApiError("some_other_error", response={"error": "some_other_error"}),
            None,
        ]
        mock_client.conversations_open.return_value = {"channel": {"id": "DM_CH"}}
        _deliver(d, try_channel="CDEMO")
        assert mock_client.chat_postMessage.call_count == 2

    def test_posts_to_dm_when_try_channel_is_none(self):
        d, mock_client = _mock_delivery("CDEMO")
        mock_client.conversations_open.return_value = {"channel": {"id": "DM_CH"}}
        _deliver(d, try_channel=None)
        assert mock_client.chat_postMessage.call_args.kwargs["channel"] == "DM_CH"

    def test_with_header_prepends_user_context_block(self):
        d, mock_client = _mock_delivery("CDEMO")
        _deliver(d, try_channel="CDEMO", with_hdr=True, user_id="USENDER")
        blocks = mock_client.chat_postMessage.call_args.kwargs["blocks"]
        assert blocks[0]["type"] == "section"
        assert "USENDER" in blocks[0]["text"]["text"]

    def test_without_header_first_block_contains_no_user_id(self):
        d, mock_client = _mock_delivery("CDEMO")
        _deliver(d, try_channel="CDEMO", with_hdr=False, user_id="USENDER")
        blocks = mock_client.chat_postMessage.call_args.kwargs["blocks"]
        assert "USENDER" not in blocks[0]["text"]["text"]

    def test_text_preview_is_truncated_to_3900_chars(self):
        d, mock_client = _mock_delivery("CDEMO")
        _deliver(d, try_channel="CDEMO", text="x" * 5000)
        assert len(mock_client.chat_postMessage.call_args.kwargs["text"]) == 3900

    def test_dm_open_failure_aborts_without_posting(self):
        d, mock_client = _mock_delivery("CDEMO")
        mock_client.chat_postMessage.side_effect = SlackApiError(
            "not_in_channel", response={"error": "not_in_channel"}
        )
        mock_client.conversations_open.return_value = {}
        _deliver(d, try_channel="CDEMO")

    def test_dm_post_failure_is_swallowed(self):
        d, mock_client = _mock_delivery()
        mock_client.conversations_open.return_value = {"channel": {"id": "DM_CH"}}
        mock_client.chat_postMessage.side_effect = SlackApiError("fatal", response={})
        _deliver(d, try_channel=None)


def _send_assignment(delivery, *, user_query="escalate please",
                     assistant_text='{"risk_level":"high","summary":"Fraud detected"}'):
    delivery.send_assignment_dm_if_needed(
        reporter_user_id="UREPORTER",
        user_query=user_query,
        assistant_text=assistant_text,
    )


class TestSendAssignmentDmIfNeeded:
    def test_no_client_returns_without_api_calls(self, monkeypatch):
        monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
        _send_assignment(SlackDelivery())

    def test_no_dm_when_notification_criteria_not_met(self):
        d, mock_client = _mock_delivery()
        _send_assignment(
            d,
            user_query="show me revenue",
            assistant_text='{"risk_level":"low","summary":"All good"}',
        )
        mock_client.chat_postMessage.assert_not_called()

    def test_sends_dm_for_high_risk_with_configured_assignee(self, monkeypatch):
        monkeypatch.setenv("SLACK_ID_DEFAULT", "UASSIGNEE")
        d, mock_client = _mock_delivery()
        mock_client.conversations_open.return_value = {"channel": {"id": "DM_CH"}}
        _send_assignment(
            d,
            user_query="check cashflow",
            assistant_text='{"risk_level":"high","summary":"Cash reserves critical"}',
        )
        mock_client.chat_postMessage.assert_called_once()
        assert mock_client.chat_postMessage.call_args.kwargs["channel"] == "DM_CH"
        assert mock_client.chat_postMessage.call_args.kwargs["text"] == "Assignment / escalation notice"

    def test_no_dm_when_no_assignee_env_var_configured(self, monkeypatch):
        for var in ("SLACK_ID_DEFAULT", "SLACK_ID_SALES", "SLACK_ID_ENGINEERING",
                    "SLACK_ID_MARKETING", "SLACK_ID_UI_UX", "SLACK_ID_BACKEND"):
            monkeypatch.delenv(var, raising=False)
        d, mock_client = _mock_delivery()
        _send_assignment(d, user_query="escalate", assistant_text='{"risk_level":"high","summary":"issue"}')
        mock_client.chat_postMessage.assert_not_called()

    def test_dm_open_failure_aborts_without_posting(self, monkeypatch):
        monkeypatch.setenv("SLACK_ID_DEFAULT", "UASSIGNEE")
        d, mock_client = _mock_delivery()
        mock_client.conversations_open.return_value = {}
        _send_assignment(d, user_query="escalate", assistant_text='{"risk_level":"high","summary":"issue"}')
        mock_client.chat_postMessage.assert_not_called()

    def test_chat_post_failure_is_swallowed(self, monkeypatch):
        monkeypatch.setenv("SLACK_ID_DEFAULT", "UASSIGNEE")
        d, mock_client = _mock_delivery()
        mock_client.conversations_open.return_value = {"channel": {"id": "DM_CH"}}
        mock_client.chat_postMessage.side_effect = SlackApiError("fatal", response={})
        _send_assignment(d, user_query="escalate", assistant_text='{"risk_level":"high","summary":"issue"}')


class TestSafeEphemeralOrDm:
    def test_no_client_returns_without_api_calls(self, monkeypatch):
        monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
        _safe_ephemeral_or_dm(SlackDelivery(), "UUSER", "oops")

    def test_dm_open_failure_aborts_without_posting(self):
        d, mock_client = _mock_delivery()
        mock_client.conversations_open.return_value = {}
        _safe_ephemeral_or_dm(d, "UUSER", "oops")
        mock_client.chat_postMessage.assert_not_called()

    def test_posts_to_dm_on_success(self):
        d, mock_client = _mock_delivery()
        mock_client.conversations_open.return_value = {"channel": {"id": "DM_CH"}}
        _safe_ephemeral_or_dm(d, "UUSER", "Something broke")
        mock_client.chat_postMessage.assert_called_once()
        assert mock_client.chat_postMessage.call_args.kwargs["channel"] == "DM_CH"

    def test_long_message_truncated_to_3900_chars(self):
        d, mock_client = _mock_delivery()
        mock_client.conversations_open.return_value = {"channel": {"id": "DM_CH"}}
        _safe_ephemeral_or_dm(d, "UUSER", "x" * 5000)
        assert len(mock_client.chat_postMessage.call_args.kwargs["text"]) == 3900

    def test_slack_api_error_on_post_is_swallowed(self):
        d, mock_client = _mock_delivery()
        mock_client.conversations_open.return_value = {"channel": {"id": "DM_CH"}}
        mock_client.chat_postMessage.side_effect = SlackApiError("fail", response={})
        _safe_ephemeral_or_dm(d, "UUSER", "msg")


def _msg_event(delivery, *, text="what is revenue", from_im=False,
               slack_user_id="UUSER", bot_user_id=None):
    handle_slack_message_event(
        delivery,
        team_id="TTEAM",
        slack_user_id=slack_user_id,
        text=text,
        bot_user_id=bot_user_id,
        from_im=from_im,
    )


class TestHandleSlackMessageEvent:
    def test_bot_self_message_is_ignored(self):
        d, _ = _mock_delivery()
        with patch.object(d, "run_agent_turn") as m:
            _msg_event(d, slack_user_id="UBOT", bot_user_id="UBOT")
        m.assert_not_called()

    def test_empty_text_after_mention_strip_is_ignored(self):
        d, _ = _mock_delivery()
        with patch.object(d, "run_agent_turn") as m:
            _msg_event(d, text="<@UBOT>")
        m.assert_not_called()

    def test_mention_prefix_stripped_before_agent_call(self):
        d, _ = _mock_delivery("CDEMO")
        with patch.object(d, "run_agent_turn", return_value={"kind": "message", "text": "ok", "intent_str": ""}) as agent_mock:
            with patch.object(d, "deliver_assistant_reply"), patch.object(d, "send_assignment_dm_if_needed"):
                _msg_event(d, text="<@UBOT> show me sales")
        assert agent_mock.call_args.args[0] == "show me sales"

    def test_error_result_sends_ephemeral_dm(self):
        d, mock_client = _mock_delivery()
        mock_client.conversations_open.return_value = {"channel": {"id": "DM_CH"}}
        with patch.object(d, "run_agent_turn", return_value={"kind": "error", "text": "oops", "intent_str": ""}):
            _msg_event(d, text="show revenue")
        assert "oops" in mock_client.chat_postMessage.call_args.kwargs["text"]

    def test_clarification_delivers_reply_but_not_assignment(self):
        d, _ = _mock_delivery()
        with patch.object(d, "run_agent_turn", return_value={"kind": "clarification", "text": "Clarify?", "intent_str": ""}):
            with patch.object(d, "deliver_assistant_reply") as deliver_mock:
                with patch.object(d, "send_assignment_dm_if_needed") as assign_mock:
                    _msg_event(d, text="ambiguous query")
        deliver_mock.assert_called_once()
        assign_mock.assert_not_called()

    def test_message_from_im_sets_no_channel_and_no_header(self):
        d, _ = _mock_delivery("CDEMO")
        with patch.object(d, "run_agent_turn", return_value={"kind": "message", "text": "ok", "intent_str": ""}):
            with patch.object(d, "deliver_assistant_reply") as deliver_mock:
                with patch.object(d, "send_assignment_dm_if_needed"):
                    _msg_event(d, text="question", from_im=True)
        kw = deliver_mock.call_args.kwargs
        assert kw["try_channel_id_first"] is None
        assert kw["with_user_context_header"] is False

    def test_message_from_channel_uses_demo_channel_with_header(self):
        d, _ = _mock_delivery("CDEMO")
        with patch.object(d, "run_agent_turn", return_value={"kind": "message", "text": "ok", "intent_str": "db"}):
            with patch.object(d, "deliver_assistant_reply") as deliver_mock:
                with patch.object(d, "send_assignment_dm_if_needed"):
                    _msg_event(d, text="question", from_im=False)
        kw = deliver_mock.call_args.kwargs
        assert kw["try_channel_id_first"] == "CDEMO"
        assert kw["with_user_context_header"] is True

    def test_message_from_channel_with_no_demo_id_yields_no_channel(self):
        d, _ = _mock_delivery("")
        with patch.object(d, "run_agent_turn", return_value={"kind": "message", "text": "ok", "intent_str": ""}):
            with patch.object(d, "deliver_assistant_reply") as deliver_mock:
                with patch.object(d, "send_assignment_dm_if_needed"):
                    _msg_event(d, text="question", from_im=False)
        assert deliver_mock.call_args.kwargs["try_channel_id_first"] is None

    def test_normal_message_calls_both_deliver_and_assignment(self):
        d, _ = _mock_delivery("CDEMO")
        with patch.object(d, "run_agent_turn", return_value={"kind": "message", "text": "result", "intent_str": "db"}):
            with patch.object(d, "deliver_assistant_reply") as deliver_mock:
                with patch.object(d, "send_assignment_dm_if_needed") as assign_mock:
                    _msg_event(d, text="revenue query")
        deliver_mock.assert_called_once()
        assign_mock.assert_called_once()


def _follow_up(delivery, *, encoded_value, source_is_im=False, source_channel_id="CSRC"):
    handle_follow_up_interaction(
        delivery,
        team_id="TTEAM",
        slack_user_id="UUSER",
        encoded_value=encoded_value,
        source_channel_id=source_channel_id,
        source_is_im=source_is_im,
    )


class TestHandleFollowUpInteraction:
    def test_invalid_base64_encoded_value_aborts(self):
        d, _ = _mock_delivery()
        with patch.object(d, "run_agent_turn") as m:
            _follow_up(d, encoded_value="not-valid-base64!!!")
        m.assert_not_called()

    def test_whitespace_only_question_aborts(self):
        encoded = base64.urlsafe_b64encode(
            json.dumps({"t": "tid", "q": "   "}).encode()
        ).decode()
        d, _ = _mock_delivery()
        with patch.object(d, "run_agent_turn") as m:
            _follow_up(d, encoded_value=encoded)
        m.assert_not_called()

    def test_error_result_sends_ephemeral_dm(self):
        d, mock_client = _mock_delivery()
        mock_client.conversations_open.return_value = {"channel": {"id": "DM_CH"}}
        with patch.object(d, "run_agent_turn", return_value={"kind": "error", "text": "failed", "intent_str": ""}):
            _follow_up(d, encoded_value=_encode("tid-1", "What is margin?"))
        assert "failed" in mock_client.chat_postMessage.call_args.kwargs["text"]

    def test_from_im_sets_no_channel(self):
        d, _ = _mock_delivery("CDEMO")
        with patch.object(d, "run_agent_turn", return_value={"kind": "message", "text": "ok", "intent_str": ""}):
            with patch.object(d, "deliver_assistant_reply") as deliver_mock:
                with patch.object(d, "send_assignment_dm_if_needed"):
                    _follow_up(d, encoded_value=_encode("tid-1", "What is margin?"), source_is_im=True)
        assert deliver_mock.call_args.kwargs["try_channel_id_first"] is None

    def test_from_channel_uses_source_channel_id(self):
        d, _ = _mock_delivery("CDEMO")
        with patch.object(d, "run_agent_turn", return_value={"kind": "message", "text": "ok", "intent_str": ""}):
            with patch.object(d, "deliver_assistant_reply") as deliver_mock:
                with patch.object(d, "send_assignment_dm_if_needed"):
                    _follow_up(d, encoded_value=_encode("tid-1", "What is margin?"), source_channel_id="CSRC99")
        assert deliver_mock.call_args.kwargs["try_channel_id_first"] == "CSRC99"

    def test_graph_thread_id_comes_from_decoded_value(self):
        d, _ = _mock_delivery("CDEMO")
        with patch.object(d, "run_agent_turn", return_value={"kind": "message", "text": "ok", "intent_str": ""}) as agent_mock:
            with patch.object(d, "deliver_assistant_reply") as deliver_mock:
                with patch.object(d, "send_assignment_dm_if_needed"):
                    _follow_up(d, encoded_value=_encode("slack_TTEAM_UUSER", "What is margin?"))
        assert agent_mock.call_args.args[1] == "slack_TTEAM_UUSER"
        assert deliver_mock.call_args.kwargs["graph_thread_id"] == "slack_TTEAM_UUSER"

    def test_normal_result_calls_both_deliver_and_assignment(self):
        d, _ = _mock_delivery("CDEMO")
        with patch.object(d, "run_agent_turn", return_value={"kind": "message", "text": "result", "intent_str": "db"}):
            with patch.object(d, "deliver_assistant_reply") as deliver_mock:
                with patch.object(d, "send_assignment_dm_if_needed") as assign_mock:
                    _follow_up(d, encoded_value=_encode("tid-1", "Explain the risk?"))
        deliver_mock.assert_called_once()
        assign_mock.assert_called_once()