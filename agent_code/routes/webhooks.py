from __future__ import annotations
from flask import Blueprint, jsonify, request, Response, stream_with_context, g
from core_logic import *

webhook_bp = Blueprint('webhook_bp', __name__)

@webhook_bp.route("/api/v1/whatsapp/webhook", methods=["GET"])
def whatsapp_verify():
    mode = request.args.get("hub.mode", "")
    token = request.args.get("hub.verify_token", "")
    challenge = request.args.get("hub.challenge", "")
    if mode == "subscribe" and token and token == WHATSAPP_VERIFY_TOKEN:
        return challenge, 200
    return "verification failed", 403


@webhook_bp.route("/api/v1/whatsapp/webhook", methods=["POST"])
def whatsapp_events():
    try:
        payload = request.get_json(force=True) or {}
        entries = payload.get("entry") or []
        for entry in entries:
            for change in entry.get("changes") or []:
                value = change.get("value") or {}
                for msg in value.get("messages") or []:
                    from_phone = str(msg.get("from") or "").strip()
                    business_id = _resolve_business_id(from_phone)
                    msg_type = msg.get("type")
                    if msg_type == "image":
                        media_id = (msg.get("image") or {}).get("id")
                        if not media_id:
                            continue
                        image_bytes, mime_type = _download_whatsapp_media(media_id)
                        extracted = _extract_bill_data_from_image(image_bytes, mime_type)
                        normalized = _normalize_bill_fields(extracted)
                        tx_id = _insert_bill_transaction(
                            business_id,
                            from_phone,
                            media_id,
                            normalized,
                            extracted,
                        )
                        analysis = _analyze_transaction(tx_id, business_id)
                        reply = (
                            f"Bill recorded successfully.\n"
                            f"Transaction ID: {tx_id}\n"
                            f"Amount: {normalized['amount']}\n"
                            f"Type: {normalized['type']}\n"
                            f"Category: {normalized['category']}\n\n"
                            f"Analysis:\n{analysis}"
                        )
                        _send_whatsapp_text(from_phone, reply)
                    elif msg_type == "text":
                        body = ((msg.get("text") or {}).get("body") or "").strip()
                        if not body:
                            continue
                        if body.lower().startswith("analyze all"):
                            answer = _analyze_business_data(business_id, body)
                        else:
                            thread_id = f"wa-{from_phone}"
                            answer = _run_agent_to_text(body, thread_id, business_id)
                        _send_whatsapp_text(from_phone, answer)
        return jsonify({"ok": True}), 200
    except Exception as exc:
        logger.error("WhatsApp webhook failed: %s", exc, exc_info=True)
        return internal_error_response(exc)


@webhook_bp.route("/api/v1/telegram/webhook", methods=["POST"])
def telegram_webhook():
    try:
        update = request.get_json(force=True) or {}
        msg = update.get("message") or update.get("edited_message") or {}
        if not msg:
            return jsonify({"ok": True})

        chat = msg.get("chat") or {}
        chat_id = chat.get("id")
        if chat_id is None:
            return jsonify({"ok": True})

        business_id = _resolve_business_id(None)

        photos = msg.get("photo") or []
        caption = (msg.get("caption") or "").strip()
        text = (msg.get("text") or "").strip()

        if photos:
            largest = max(photos, key=lambda p: p.get("file_size", 0))
            file_id = largest.get("file_id")
            if file_id:
                image_bytes, mime_type = _download_telegram_file(file_id)
                extracted = _extract_bill_data_from_image(image_bytes, mime_type)
                normalized = _normalize_bill_fields(extracted)
                tx_id = _insert_bill_transaction(
                    business_id,
                    None,
                    file_id,
                    normalized,
                    extracted,
                )
                analysis = _analyze_transaction(tx_id, business_id)
                reply = (
                    f"Bill recorded successfully.\n"
                    f"Transaction ID: {tx_id}\n"
                    f"Amount: {normalized['amount']}\n"
                    f"Type: {normalized['type']}\n"
                    f"Category: {normalized['category']}\n\n"
                    f"Analysis:\n{analysis}"
                )
                _send_telegram_text(chat_id, reply)
                return jsonify({"ok": True})

        content = text or caption
        if content:
            if content.lower().startswith("analyze all"):
                answer = _analyze_business_data(business_id, content)
            else:
                thread_id = f"tg-{chat_id}"
                answer = _run_agent_to_text(content, thread_id, business_id)
            _send_telegram_text(chat_id, answer)

        return jsonify({"ok": True})
    except Exception as exc:
        logger.error("Telegram webhook failed: %s", exc, exc_info=True)
        return internal_error_response(exc)


ASSIGNMENTS_FILE = "assigned_issues.json"


def get_assigned_counts():
    if not os.path.exists(ASSIGNMENTS_FILE):
        return {}
    try:
        with open(ASSIGNMENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def increment_assigned_count(username: str):
    counts = get_assigned_counts()
    counts[username] = counts.get(username, 0) + 1
    with open(ASSIGNMENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(counts, f)


