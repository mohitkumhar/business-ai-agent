"""Flask routes: `/slack/events` (Events API) and `/slack/interactive` (Block Kit actions)."""

from __future__ import annotations

import json
import os
import threading
from urllib.parse import parse_qs

from flask import Blueprint, jsonify, request

from logger.logger import logger

slack_bp = Blueprint("slack_integration", __name__, url_prefix="/slack")


def register_slack_routes(app) -> None:
    app.register_blueprint(slack_bp)


def _signing_secret() -> str:
    return (os.getenv("SLACK_SIGNING_SECRET") or "").strip()


def _verify_slack_request(raw_body: bytes) -> bool:
    secret = _signing_secret()
    if not secret:
        return False
    try:
        from slack_sdk.signature import SignatureVerifier

        sig = request.headers.get("X-Slack-Signature", "")
        ts = request.headers.get("X-Slack-Request-Timestamp", "")
        return SignatureVerifier(secret).is_valid(raw_body, ts, sig)
    except Exception as e:
        logger.warning("Slack signature verify error: %s", e)
        return False


def _slack_configured() -> bool:
    return bool((os.getenv("SLACK_BOT_TOKEN") or "").strip() and _signing_secret())


@slack_bp.route("/events", methods=["POST"])
def slack_events():
    raw = request.get_data()
    if not _slack_configured():
        return jsonify({"ok": True, "warning": "slack not configured"}), 200
    if not _verify_slack_request(raw):
        return "", 403

    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return "", 400

    if data.get("type") == "url_verification":
        return jsonify({"challenge": data.get("challenge", "")})

    if data.get("type") != "event_callback":
        return jsonify({"ok": True})

    event = data.get("event") or {}
    if event.get("bot_id") or event.get("subtype"):
        return jsonify({"ok": True})

    team_id = str(data.get("team_id") or "")

    def worker():
        try:
            from slack_integration.slack_handler import (
                SlackDelivery,
                handle_slack_message_event,
            )

            delivery = SlackDelivery()
            if not delivery.configured():
                return

            bot_uid = (os.getenv("SLACK_BOT_USER_ID") or "").strip() or None
            if not bot_uid:
                auths = data.get("authorizations") or []
                for a in auths:
                    if isinstance(a, dict) and a.get("is_bot"):
                        bot_uid = str(a.get("user_id") or "") or None
                        break

            et = event.get("type")
            if et == "app_mention":
                uid = str(event.get("user") or "")
                text = str(event.get("text") or "")
                handle_slack_message_event(
                    delivery,
                    team_id=team_id,
                    slack_user_id=uid,
                    text=text,
                    bot_user_id=bot_uid,
                    from_im=False,
                )
                return

            if et == "message":
                ch = event.get("channel_type")
                if ch != "im":
                    return
                uid = str(event.get("user") or "")
                text = str(event.get("text") or "")
                handle_slack_message_event(
                    delivery,
                    team_id=team_id,
                    slack_user_id=uid,
                    text=text,
                    bot_user_id=bot_uid,
                    from_im=True,
                )
        except Exception:
            logger.exception("Slack event worker failed")

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"ok": True})


@slack_bp.route("/interactive", methods=["POST"])
def slack_interactive():
    raw = request.get_data()
    if not _slack_configured():
        return "", 200
    if not _verify_slack_request(raw):
        return "", 403

    try:
        form = parse_qs(raw.decode("utf-8"))
        payload_raw = (form.get("payload") or ["{}"])[0]
        payload = json.loads(payload_raw)
    except (json.JSONDecodeError, UnicodeDecodeError, IndexError, TypeError):
        return "", 400

    if payload.get("type") != "block_actions":
        return jsonify({"ok": True})

    team_id = str((payload.get("team") or {}).get("id") or "")
    user_id = str((payload.get("user") or {}).get("id") or "")
    ch_meta = payload.get("channel") or {}
    source_channel_id = str(ch_meta.get("id") or "")
    source_is_im = ch_meta.get("name") == "directmessage"
    actions = payload.get("actions") or []

    actions = payload.get("actions") or []
    action_item = None
    for a in actions:
        if isinstance(a, dict):
            aid = a.get("action_id")
            if aid in ("agent_follow_up", "escalation_assign", "escalation_dismiss"):
                action_item = a
                break
    if not action_item:
        return jsonify({"ok": True})

    action_id = action_item.get("action_id")
    encoded = str(action_item.get("value") or "")

    def handle_escalations():
        try:
            import requests
            response_url = payload.get("response_url")
            if not response_url:
                return

            if action_id == "escalation_assign":
                msg_blocks = payload.get("message", {}).get("blocks", [])
                if msg_blocks and msg_blocks[-1].get("type") == "actions":
                    msg_blocks.pop()
                msg_blocks.append({
                    "type": "context",
                    "elements": [{"type": "mrkdwn", "text": f"✅ Assigned to <@{encoded}> by <@{user_id}>"}]
                })
                requests.post(response_url, json={"replace_original": True, "blocks": msg_blocks})

                from slack_integration.slack_handler import SlackDelivery
                delivery = SlackDelivery()
                if delivery.configured():
                    dm = delivery._open_dm_channel(encoded)
                    if dm:
                        delivery.client.chat_postMessage(
                            channel=dm,
                            text=f"Hello! <@{user_id}> has manually assigned an issue to you from the web chatbot. Please check the channel.",
                        )
            
            elif action_id == "escalation_dismiss":
                msg_blocks = payload.get("message", {}).get("blocks", [])
                if msg_blocks and msg_blocks[-1].get("type") == "actions":
                    msg_blocks.pop()
                msg_blocks.append({
                    "type": "context",
                    "elements": [{"type": "mrkdwn", "text": f"❌ Dismissed by <@{user_id}>"}]
                })
                requests.post(response_url, json={"replace_original": True, "blocks": msg_blocks})

        except Exception as e:
            logger.exception("Slack interactive escalation failed")

    if action_id in ("escalation_assign", "escalation_dismiss"):
        threading.Thread(target=handle_escalations, daemon=True).start()
        return jsonify({"ok": True})

    def worker():
        try:
            from slack_integration.slack_handler import (
                SlackDelivery,
                handle_follow_up_interaction,
            )

            delivery = SlackDelivery()
            if not delivery.configured():
                return
            handle_follow_up_interaction(
                delivery,
                team_id=team_id,
                slack_user_id=user_id,
                encoded_value=encoded,
                source_channel_id=source_channel_id,
                source_is_im=source_is_im,
            )
        except Exception:
            logger.exception("Slack interactive worker failed")

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"ok": True})
