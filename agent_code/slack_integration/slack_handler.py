"""Run the agent, post to #demo (or DM fallback), optional assignee DM, and parse SSE."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from logger.logger import logger
from query_execution import stream_agent_sse_lines
from slack_integration.slack_formatter import (
    build_assignment_dm_blocks,
    build_reply_blocks,
    decode_followup_value,
)
from slack_integration.smart_assigner import (
    extract_risk_and_summary,
    parse_business_envelope,
    pick_assignee_slack_id,
    should_notify_assignee,
    slack_thread_id,
)
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

_MENTION = re.compile(r"<@[^>]+>\s*")

_DEMO_FAIL_ERRORS = frozenset(
    {
        "not_in_channel",
        "channel_not_found",
        "is_archived",
        "missing_scope",
        "invalid_auth",
        "account_inactive",
    }
)


def strip_slack_mentions(text: str) -> str:
    return _MENTION.sub("", text or "").strip()


def _event_from_sse_chunk(chunk: str) -> dict[str, Any] | None:
    for line in chunk.strip().split("\n"):
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].lstrip()
        if not payload:
            continue
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return None
    return None


class SlackDelivery:
    def __init__(self) -> None:
        token = (os.getenv("SLACK_BOT_TOKEN") or "").strip()
        self._client = WebClient(token=token) if token else None
        self.demo_channel_id = (os.getenv("SLACK_DEMO_CHANNEL_ID") or "").strip()

    @property
    def client(self) -> WebClient | None:
        return self._client

    def configured(self) -> bool:
        return self._client is not None

    def run_agent_turn(
        self, user_query: str, graph_thread_id: str, business_id: str = ""
    ) -> dict[str, Any]:
        assistant_chunks: list[str] = []
        intent_str = ""
        for chunk in stream_agent_sse_lines(user_query, graph_thread_id, business_id):
            evt = _event_from_sse_chunk(chunk)
            if not evt:
                continue
            t = evt.get("type")
            if t == "token":
                assistant_chunks.append(str(evt.get("content", "")))
            elif t == "final":
                intent_str = str(evt.get("intent_str", "") or intent_str)
            elif t == "clarification":
                return {
                    "kind": "clarification",
                    "text": str(evt.get("clarification", "")),
                    "intent_str": str(evt.get("intent_str", "")),
                }
            elif t == "error":
                return {
                    "kind": "error",
                    "text": str(evt.get("error", "Unknown error")),
                    "intent_str": str(evt.get("intent_str", "")),
                }
        text = "".join(assistant_chunks)
        return {"kind": "message", "text": text, "intent_str": intent_str}

    def _open_dm_channel(self, slack_user_id: str) -> str | None:
        assert self._client is not None
        try:
            o = self._client.conversations_open(users=slack_user_id)
            return str(o["channel"]["id"])
        except (SlackApiError, KeyError, TypeError) as e:
            logger.warning("conversations_open failed for %s: %s", slack_user_id, e)
            return None

    def deliver_assistant_reply(
        self,
        *,
        slack_user_id: str,
        assistant_text: str,
        intent_str: str,
        graph_thread_id: str,
        user_query_for_context: str,
        try_channel_id_first: str | None,
        with_user_context_header: bool,
    ) -> None:
        """
        Try ``try_channel_id_first`` (e.g. #demo or the channel where a button was clicked);
        on expected Slack errors, fall back to the user's DM. No user-facing crash.
        If ``try_channel_id_first`` is None (bot was contacted via DM), post only to DM.
        """
        if not self._client:
            return
        blocks = build_reply_blocks(
            assistant_text, thread_id=graph_thread_id, intent_str=intent_str
        )
        preview = (assistant_text or "").strip() or " "
        preview = preview[:3900]

        header_context = (
            [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*From* <@{slack_user_id}>\n*Question:*\n```{_truncate_block(user_query_for_context, 800)}```",
                    },
                }
            ]
            if with_user_context_header
            else []
        )

        if try_channel_id_first:
            try:
                self._client.chat_postMessage(
                    channel=try_channel_id_first,
                    text=preview,
                    blocks=header_context + blocks,
                )
                return
            except SlackApiError as e:
                err = (e.response or {}).get("error", "")
                if err in _DEMO_FAIL_ERRORS:
                    logger.info(
                        "Channel post failed (%s); falling back to user DM.", err
                    )
                else:
                    logger.warning("Unexpected Slack error on channel post: %s", e)

        dm_ch = self._open_dm_channel(slack_user_id)
        if not dm_ch:
            return
        try:
            self._client.chat_postMessage(
                channel=dm_ch,
                text=preview,
                blocks=blocks,
            )
        except SlackApiError as e:
            logger.warning("DM chat_postMessage failed: %s", e)

    def send_assignment_dm_if_needed(
        self,
        *,
        reporter_user_id: str,
        user_query: str,
        assistant_text: str,
    ) -> None:
        if not self._client:
            return
        env = parse_business_envelope(assistant_text)
        risk, summary = extract_risk_and_summary(env, assistant_text)
        if not should_notify_assignee(
            user_query=user_query, risk_level=risk, summary=summary
        ):
            return
        assignee = pick_assignee_slack_id(user_query=user_query, summary=summary)
        if not assignee:
            logger.info("Assignment criteria met but no SLACK_ID_* assignee configured.")
            return
        dm_ch = self._open_dm_channel(assignee)
        if not dm_ch:
            return
        blocks = build_assignment_dm_blocks(
            reporter_user_id=reporter_user_id,
            user_query=user_query,
            summary=summary or assistant_text[:2000],
            risk_level=risk,
        )
        try:
            self._client.chat_postMessage(
                channel=dm_ch,
                text="Assignment / escalation notice",
                blocks=blocks,
            )
        except SlackApiError as e:
            logger.warning("Assignment DM failed: %s", e)


def _truncate_block(s: str, n: int) -> str:
    s = s or ""
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


def handle_slack_message_event(
    delivery: SlackDelivery,
    *,
    team_id: str,
    slack_user_id: str,
    text: str,
    bot_user_id: str | None,
    from_im: bool,
) -> None:
    """Entry point from Events API (already filtered for bot / empty)."""
    if bot_user_id and slack_user_id == bot_user_id:
        return
    q = strip_slack_mentions(text)
    if not q:
        return
    graph_tid = slack_thread_id(team_id, slack_user_id)
    business_id = (os.getenv("DEFAULT_BUSINESS_ID") or "").strip()
    result = delivery.run_agent_turn(q, graph_tid, business_id=business_id)
    if result["kind"] == "error":
        _safe_ephemeral_or_dm(
            delivery,
            slack_user_id,
            f"Something went wrong: {result.get('text', 'error')}",
        )
        return
    try_ch = None if from_im else (delivery.demo_channel_id or None)
    with_hdr = bool(try_ch and delivery.demo_channel_id and try_ch == delivery.demo_channel_id)

    if result["kind"] == "clarification":
        delivery.deliver_assistant_reply(
            slack_user_id=slack_user_id,
            assistant_text=str(result.get("text", "")),
            intent_str=str(result.get("intent_str", "")),
            graph_thread_id=graph_tid,
            user_query_for_context=q,
            try_channel_id_first=try_ch,
            with_user_context_header=with_hdr,
        )
        return

    assistant_text = str(result.get("text", ""))
    intent_str = str(result.get("intent_str", ""))
    delivery.deliver_assistant_reply(
        slack_user_id=slack_user_id,
        assistant_text=assistant_text,
        intent_str=intent_str,
        graph_thread_id=graph_tid,
        user_query_for_context=q,
        try_channel_id_first=try_ch,
        with_user_context_header=with_hdr,
    )
    delivery.send_assignment_dm_if_needed(
        reporter_user_id=slack_user_id,
        user_query=q,
        assistant_text=assistant_text,
    )


def _safe_ephemeral_or_dm(delivery: SlackDelivery, slack_user_id: str, msg: str) -> None:
    if not delivery.client:
        return
    ch = delivery._open_dm_channel(slack_user_id)
    if not ch:
        return
    try:
        delivery.client.chat_postMessage(channel=ch, text=msg[:3900])
    except SlackApiError:
        pass


def handle_follow_up_interaction(
    delivery: SlackDelivery,
    *,
    team_id: str,
    slack_user_id: str,
    encoded_value: str,
    source_channel_id: str,
    source_is_im: bool,
) -> None:
    decoded = decode_followup_value(encoded_value)
    if not decoded:
        return
    graph_tid, question = decoded
    if not question.strip():
        return
    business_id = (os.getenv("DEFAULT_BUSINESS_ID") or "").strip()
    result = delivery.run_agent_turn(question, graph_tid, business_id=business_id)
    if result["kind"] == "error":
        _safe_ephemeral_or_dm(
            delivery, slack_user_id, f"Follow-up failed: {result.get('text', '')}"
        )
        return
    if result["kind"] == "clarification":
        assistant_text = str(result.get("text", ""))
    else:
        assistant_text = str(result.get("text", ""))
    intent_str = str(result.get("intent_str", ""))
    try_ch = None if source_is_im else (source_channel_id or None)
    with_hdr = bool(
        try_ch
        and delivery.demo_channel_id
        and try_ch == delivery.demo_channel_id
    )
    delivery.deliver_assistant_reply(
        slack_user_id=slack_user_id,
        assistant_text=assistant_text,
        intent_str=intent_str,
        graph_thread_id=graph_tid,
        user_query_for_context=question,
        try_channel_id_first=try_ch,
        with_user_context_header=with_hdr,
    )
    delivery.send_assignment_dm_if_needed(
        reporter_user_id=slack_user_id,
        user_query=question,
        assistant_text=assistant_text,
    )
