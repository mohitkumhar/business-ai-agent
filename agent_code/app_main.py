from __future__ import annotations

import base64
import json
import os
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Any

import requests
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request, stream_with_context, g
from flask_cors import CORS
from langchain_core.messages import HumanMessage, SystemMessage
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, Counter, Histogram, generate_latest

from api_errors import internal_error_response
from db_config import execute_read_query_params, get_db_connection
from auth_passwords import SOCIAL_LOGIN_PASSWORD_HASH
from llm.base_llm import base_llm
from logger.logger import logger
from query_execution import stream_agent_sse_lines
from auth import AuthError, decode_jwt_identity, require_jwt_secret

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = require_jwt_secret(os.getenv("JWT_SECRET"))
CORS(app)

AGENT_REQUEST_COUNT = Counter(
    "agent_requests_total",
    "Total requests to the agent API",
    ["method", "endpoint", "status"],
)
AGENT_REQUEST_LATENCY = Histogram(
    "agent_request_duration_seconds",
    "Agent API request latency",
    ["method", "endpoint"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120],
)
AGENT_INTENT_COUNT = Counter(
    "agent_intent_detections_total",
    "Total intent detections by type",
    ["intent"],
)

WHATSAPP_VERIFY_TOKEN = (os.getenv("WHATSAPP_VERIFY_TOKEN") or "").strip()
WHATSAPP_ACCESS_TOKEN = (os.getenv("WHATSAPP_ACCESS_TOKEN") or "").strip()
WHATSAPP_PHONE_NUMBER_ID = (os.getenv("WHATSAPP_PHONE_NUMBER_ID") or "").strip()
TELEGRAM_BOT_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
DEFAULT_BUSINESS_ID = (os.getenv("DEFAULT_BUSINESS_ID") or "").strip()


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            identity = decode_jwt_identity(
                request.headers.get("Authorization"),
                app.config["SECRET_KEY"],
            )
        except AuthError as exc:
            return jsonify({"message": exc.message}), exc.status_code

        g.user_id = identity["user_id"]
        g.business_id = identity["business_id"]
        return f(*args, **kwargs)

    return decorated


def get_current_business_id():
    return getattr(g, "business_id", None)


@app.before_request
def _start_timer():
    g.start_time = time.time()


@app.after_request
def _record_metrics(response):
    if request.path == "/metrics":
        return response
    latency = time.time() - getattr(g, "start_time", time.time())
    endpoint = request.endpoint or "unknown"
    AGENT_REQUEST_COUNT.labels(request.method, endpoint, response.status_code).inc()
    AGENT_REQUEST_LATENCY.labels(request.method, endpoint).observe(latency)
    return response


def _sse_stream_response(generator):
    resp = Response(stream_with_context(generator), mimetype="text/event-stream")
    resp.headers["Cache-Control"] = "no-cache, no-transform"
    resp.headers["X-Accel-Buffering"] = "no"
    resp.headers["Connection"] = "keep-alive"
    return resp


def _json_from_llm_text(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return {}
    return {}


def _ensure_whatsapp_tables():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS public.whatsapp_contacts (
                    phone TEXT PRIMARY KEY,
                    business_id UUID NOT NULL REFERENCES public.businesses(business_id) ON DELETE CASCADE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS public.billing_ingestions (
                    ingestion_id BIGSERIAL PRIMARY KEY,
                    business_id UUID NOT NULL REFERENCES public.businesses(business_id) ON DELETE CASCADE,
                    source TEXT NOT NULL,
                    sender_phone TEXT,
                    media_id TEXT,
                    transaction_id BIGINT REFERENCES public.daily_transactions(transaction_id) ON DELETE SET NULL,
                    extracted_json JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        conn.commit()
    finally:
        conn.close()


_ensure_whatsapp_tables()
try:
    from slack_integration.flask_routes import register_slack_routes

    register_slack_routes(app)
except ImportError as exc:
    logger.warning("Slack integration not registered: %s", exc)


def _resolve_business_id(phone: str | None) -> str:
    if phone:
        rows = execute_read_query_params(
            "SELECT business_id FROM public.whatsapp_contacts WHERE phone = %s LIMIT 1",
            (phone,),
        )
        if rows:
            return str(rows[0]["business_id"])
    if DEFAULT_BUSINESS_ID:
        return DEFAULT_BUSINESS_ID
    rows = execute_read_query_params(
        "SELECT business_id FROM public.businesses ORDER BY created_at DESC LIMIT 1"
    )
    if not rows:
        raise ValueError("No business available. Onboard business or set DEFAULT_BUSINESS_ID.")
    return str(rows[0]["business_id"])


def _run_agent_to_text(query: str, thread_id: str, business_id: str) -> str:
    full = []
    fallback_error = None
    for line in stream_agent_sse_lines(
        query,
        thread_id,
        business_id,
        on_chain_intent=lambda n: AGENT_INTENT_COUNT.labels(n).inc(),
    ):
        if not line.startswith("data: "):
            continue
        payload = line[6:].strip()
        if not payload:
            continue
        try:
            evt = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if evt.get("type") == "token":
            full.append(evt.get("content", ""))
        elif evt.get("type") == "error":
            fallback_error = evt.get("error")
    text = "".join(full).strip()
    if text:
        return text
    if fallback_error:
        return f"Sorry, I hit an error: {fallback_error}"
    return "I could not generate a response."


def _download_whatsapp_media(media_id: str) -> tuple[bytes, str]:
    if not WHATSAPP_ACCESS_TOKEN:
        raise ValueError("WHATSAPP_ACCESS_TOKEN is not configured.")
    meta = requests.get(
        f"https://graph.facebook.com/v21.0/{media_id}",
        headers={"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"},
        timeout=30,
    )
    meta.raise_for_status()
    meta_json = meta.json()
    media_url = meta_json.get("url")
    mime_type = meta_json.get("mime_type") or "image/jpeg"
    if not media_url:
        raise ValueError("Media URL missing in WhatsApp response.")
    blob = requests.get(
        media_url,
        headers={"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"},
        timeout=60,
    )
    blob.raise_for_status()
    return blob.content, mime_type


def _download_telegram_file(file_id: str) -> tuple[bytes, str]:
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not configured.")
    meta = requests.get(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile",
        params={"file_id": file_id},
        timeout=30,
    )
    meta.raise_for_status()
    info = meta.json().get("result") or {}
    file_path = info.get("file_path")
    if not file_path:
        raise ValueError("Telegram getFile missing file_path.")
    url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
    blob = requests.get(url, timeout=60)
    blob.raise_for_status()
    return blob.content, "image/jpeg"


def _extract_bill_data_from_image(image_bytes: bytes, mime_type: str) -> dict[str, Any]:
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:{mime_type};base64,{b64}"
    msgs = [
        SystemMessage(
            content=(
                "You extract bill/invoice data. Return ONLY JSON with keys: "
                "vendor_name, amount, transaction_date(YYYY-MM-DD), type(Revenue|Expense), "
                "category, description, confidence(0..1)."
            )
        ),
        HumanMessage(
            content=[
                {"type": "text", "text": "Extract billing details from this image."},
                {"type": "image_url", "image_url": {"url": data_url}},
            ]
        ),
    ]
    res = base_llm.invoke(msgs)
    text = res.content if isinstance(res.content, str) else json.dumps(res.content)
    extracted = _json_from_llm_text(text)
    return extracted if isinstance(extracted, dict) else {}


def _normalize_bill_fields(extracted: dict[str, Any]) -> dict[str, Any]:
    amount = extracted.get("amount")
    try:
        amount = float(amount) if amount is not None else 0.0
    except (ValueError, TypeError):
        amount = 0.0
    tx_date = str(extracted.get("transaction_date") or datetime.utcnow().date().isoformat())
    ttype = str(extracted.get("type") or "Expense").strip().lower()
    if ttype not in ("revenue", "expense"):
        ttype = "expense"
    category = str(extracted.get("category") or extracted.get("vendor_name") or "Uncategorized")
    description = str(extracted.get("description") or extracted.get("vendor_name") or "Bill ingestion")
    return {
        "amount": max(amount, 0.0),
        "transaction_date": tx_date,
        "type": "Revenue" if ttype == "revenue" else "Expense",
        "category": category[:100],
        "description": description,
        "vendor_name": str(extracted.get("vendor_name") or "").strip(),
        "confidence": extracted.get("confidence", None),
    }


def _insert_bill_transaction(
    business_id: str,
    sender_phone: str | None,
    media_id: str,
    normalized: dict[str, Any],
    extracted: dict[str, Any],
) -> int:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.daily_transactions (business_id, transaction_date, type, category, amount, description)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING transaction_id
                """,
                (
                    business_id,
                    normalized["transaction_date"],
                    normalized["type"],
                    normalized["category"],
                    normalized["amount"],
                    normalized["description"],
                ),
            )
            tx_id = int(cur.fetchone()[0])
            cur.execute(
                """
                INSERT INTO public.billing_ingestions (business_id, source, sender_phone, media_id, transaction_id, extracted_json)
                VALUES (%s, 'whatsapp', %s, %s, %s, %s::jsonb)
                """,
                (business_id, sender_phone, media_id, tx_id, json.dumps(extracted)),
            )
        conn.commit()
        return tx_id
    finally:
        conn.close()


def _analyze_transaction(transaction_id: int, business_id: str) -> str:
    rows = execute_read_query_params(
        """
        SELECT transaction_id, transaction_date, type, category, amount, description
        FROM public.daily_transactions
        WHERE transaction_id = %s AND business_id = %s
        """,
        (transaction_id, business_id),
    )
    if not rows:
        return "Bill captured but transaction not found for analysis."
    tx = rows[0]
    month_rows = execute_read_query_params(
        """
        SELECT
            COALESCE(SUM(CASE WHEN type='Revenue' THEN amount END), 0) AS month_revenue,
            COALESCE(SUM(CASE WHEN type='Expense' THEN amount END), 0) AS month_expense
        FROM public.daily_transactions
        WHERE business_id = %s
          AND date_trunc('month', transaction_date) = date_trunc('month', %s::date)
        """,
        (business_id, tx["transaction_date"]),
    )
    prompt = (
        "You are a business finance analyst. Give concise analysis for this bill and impact.\n"
        f"Transaction: {json.dumps(tx, default=str)}\n"
        f"Monthly totals: {json.dumps(month_rows[0] if month_rows else {}, default=str)}\n"
        "Return a short paragraph plus 3 bullet recommendations."
    )
    res = base_llm.invoke(prompt)
    return res.content if isinstance(res.content, str) else json.dumps(res.content)


def _analyze_business_data(business_id: str, user_question: str) -> str:
    summary = execute_read_query_params(
        """
        SELECT
            COALESCE(SUM(CASE WHEN type='Revenue' THEN amount END), 0) AS total_revenue,
            COALESCE(SUM(CASE WHEN type='Expense' THEN amount END), 0) AS total_expense,
            COUNT(*) AS transaction_count
        FROM public.daily_transactions
        WHERE business_id = %s
        """,
        (business_id,),
    )
    recent = execute_read_query_params(
        """
        SELECT transaction_date, type, category, amount, description
        FROM public.daily_transactions
        WHERE business_id = %s
        ORDER BY transaction_date DESC, transaction_id DESC
        LIMIT 25
        """,
        (business_id,),
    )
    prompt = (
        "You are a business analyst. Answer user question based on business transaction data.\n"
        f"Question: {user_question}\n"
        f"Summary: {json.dumps(summary[0] if summary else {}, default=str)}\n"
        f"Recent transactions: {json.dumps(recent, default=str)}\n"
        "Answer clearly with actionable suggestions."
    )
    res = base_llm.invoke(prompt)
    return res.content if isinstance(res.content, str) else json.dumps(res.content)


def _send_whatsapp_text(to_number: str, text: str):
    if not (WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID):
        logger.warning("WhatsApp send skipped; credentials not configured.")
        return
    body = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"preview_url": False, "body": text[:4096]},
    }
    requests.post(
        f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_NUMBER_ID}/messages",
        headers={
            "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=30,
    ).raise_for_status()


def _send_telegram_text(chat_id: int, text: str):
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram send skipped; TELEGRAM_BOT_TOKEN not configured.")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text[:4096]},
            timeout=30,
        ).raise_for_status()
    except Exception as exc:
        logger.error("Failed to send Telegram message: %s", exc, exc_info=True)


@app.route("/")
def home():
    return "Intelligent AI Agent is running. Use /api/v1/query."


@app.route("/metrics")
def metrics_endpoint():
    return Response(generate_latest(REGISTRY), mimetype=CONTENT_TYPE_LATEST)


@app.route("/api/v1/query", methods=["POST", "GET"])
def query_agent():
    input_query = request.args.get("input-query", "")
    thread_id = request.args.get("thread-id", "")
    business_id = request.args.get("business-id", "") or ""
    if not input_query:
        return jsonify({"is_error": True, "error": "input query is required"}), 400
    if not thread_id:
        return jsonify({"is_error": True, "error": "thread-id is required"}), 400
    gen = stream_agent_sse_lines(
        input_query,
        thread_id,
        business_id,
        on_chain_intent=lambda n: AGENT_INTENT_COUNT.labels(n).inc(),
    )
    return _sse_stream_response(gen)


@app.route("/api/v1/billing/analyze-all", methods=["POST"])
def billing_analyze_all():
    data = request.get_json(force=True) or {}
    question = (data.get("question") or "Analyze all business billing data").strip()
    business_id = (data.get("business_id") or "").strip() or _resolve_business_id(None)
    try:
        answer = _analyze_business_data(business_id, question)
        return jsonify({"business_id": business_id, "analysis": answer})
    except Exception as exc:
        logger.error("Analyze all failed: %s", exc, exc_info=True)
        return internal_error_response(exc)


@app.route("/api/v1/whatsapp/webhook", methods=["GET"])
def whatsapp_verify():
    mode = request.args.get("hub.mode", "")
    token = request.args.get("hub.verify_token", "")
    challenge = request.args.get("hub.challenge", "")
    if mode == "subscribe" and token and token == WHATSAPP_VERIFY_TOKEN:
        return challenge, 200
    return "verification failed", 403


@app.route("/api/v1/whatsapp/webhook", methods=["POST"])
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


@app.route("/api/v1/telegram/webhook", methods=["POST"])
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


@app.route("/api/v1/employees", methods=["GET"])
def get_employees():
    repo = os.getenv("GITHUB_REPO", "mohitkumhar/intelligent-business-agent")
    try:
        res = requests.get(f"https://api.github.com/repos/{repo}/contributors", timeout=20)
        counts = get_assigned_counts()
        if res.status_code != 200:
            return jsonify(
                {
                    "employees": [
                        {"login": "engineer_a", "avatar_url": "", "assigned_issues": counts.get("engineer_a", 0)},
                        {"login": "engineer_b", "avatar_url": "", "assigned_issues": counts.get("engineer_b", 0)},
                    ]
                }
            )
        contributors = res.json()
        return jsonify(
            {
                "employees": [
                    {
                        "login": c.get("login", "Unknown"),
                        "avatar_url": c.get("avatar_url", ""),
                        "assigned_issues": counts.get(c.get("login", "Unknown"), 0),
                    }
                    for c in contributors
                ]
            }
        )
    except Exception as exc:
        return internal_error_response(exc)


@app.route("/api/v1/escalate", methods=["POST"])
def escalate_to_slack():
    try:
        data = request.get_json() or {}
        query = data.get("query", "No specific query")
        summary = data.get("summary", "No summary provided")
        from slack_integration.slack_handler import SlackDelivery
        from slack_integration.smart_assigner import pick_assignee_slack_id

        delivery = SlackDelivery()
        if not delivery.configured():
            return jsonify({"error": "Slack is not configured"}), 500
        ch = delivery.demo_channel_id
        if not ch:
            return jsonify({"error": "No Slack channel configured"}), 500

        assignee_id = data.get("assignee_name") or pick_assignee_slack_id(user_query=query, summary=summary)
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "Web User Escalation", "emoji": True},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Query:*\n>{query[:500]}\n\n*Context:*\n```{summary[:2000]}```"},
            },
        ]
        if assignee_id:
            increment_assigned_count(str(assignee_id))
        delivery.client.chat_postMessage(channel=ch, text="Web Chatbot Escalation", blocks=blocks)
        return jsonify({"status": "ok"}), 200
    except Exception as exc:
        return internal_error_response(exc)


@app.route("/api/dashboard/summary", methods=["GET", "OPTIONS"])
def api_dashboard_summary():
    cutoff = (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%d")
    try:
        txn = execute_read_query_params(
            """
            SELECT
                COALESCE(SUM(CASE WHEN type='Revenue' THEN amount END), 0) AS total_revenue,
                COALESCE(SUM(CASE WHEN type='Expense' THEN amount END), 0) AS total_expenses,
                COUNT(*) AS total_transactions
            FROM daily_transactions
            WHERE transaction_date >= %s
            """,
            (cutoff,),
        )
        alerts = execute_read_query_params(
            "SELECT COUNT(*) AS active_alerts FROM alerts WHERE status='Active' AND created_at >= %s",
            (cutoff,),
        )
        row = txn[0] if txn else {}
        arow = alerts[0] if alerts else {}
        return jsonify(
            {
                "total_revenue": float(row.get("total_revenue", 0)),
                "total_expenses": float(row.get("total_expenses", 0)),
                "net_profit": float(row.get("total_revenue", 0)) - float(row.get("total_expenses", 0)),
                "total_transactions": int(row.get("total_transactions", 0)),
                "active_alerts": int(arow.get("active_alerts", 0)),
            }
        )
    except Exception as exc:
        return internal_error_response(exc)


@app.route("/api/dashboard/financial-overview", methods=["GET", "OPTIONS"])
def api_financial_overview():
    try:
        rows = execute_read_query_params(
            """
            SELECT year, month,
                   COALESCE(SUM(total_revenue),0) AS total_revenue,
                   COALESCE(SUM(total_expenses),0) AS total_expenses,
                   COALESCE(SUM(net_profit),0) AS net_profit,
                   COALESCE(SUM(cash_balance),0) AS cash_balance
            FROM financial_records
            GROUP BY year, month
            ORDER BY year DESC, month DESC
            LIMIT 12
            """
        )
        rows = list(rows)
        rows.reverse()
        labels = [f"{r['year']}-{str(r['month']).zfill(2)}" for r in rows]
        return jsonify(
            {
                "labels": labels,
                "revenue": [float(r["total_revenue"]) for r in rows],
                "expenses": [float(r["total_expenses"]) for r in rows],
                "net_profit": [float(r["net_profit"]) for r in rows],
                "cash_balance": [float(r["cash_balance"]) for r in rows],
            }
        )
    except Exception as exc:
        return internal_error_response(exc)


@app.route("/api/dashboard/revenue-vs-expense", methods=["GET", "OPTIONS"])
@token_required
def api_revenue_vs_expense():
    bid = get_current_business_id()
    period = request.args.get("period", "this_month")
    start_date, end_date = get_period_dates(period)
    try:
        rows = execute_read_query_params(
            """
            SELECT category, type, COALESCE(SUM(amount), 0) AS total
            FROM daily_transactions
            WHERE business_id = %s AND transaction_date BETWEEN %s AND %s
            GROUP BY category, type
            ORDER BY total DESC
            """,
            (bid, start_date, end_date),
        )
        revenue_cats: dict[str, float] = {}
        expense_cats: dict[str, float] = {}
        for r in rows:
            cat = r["category"] or "Other"
            amt = float(r["total"])
            if r["type"] == "Revenue":
                revenue_cats[cat] = revenue_cats.get(cat, 0) + amt
            else:
                expense_cats[cat] = expense_cats.get(cat, 0) + amt
        labels = sorted(set(list(revenue_cats.keys()) + list(expense_cats.keys())))
        return jsonify(
            {"labels": labels, "revenue": [revenue_cats.get(c, 0) for c in labels], "expenses": [expense_cats.get(c, 0) for c in labels]}
        )
    except Exception as exc:
        return internal_error_response(exc)


@app.route("/api/dashboard/sales-trend", methods=["GET", "OPTIONS"])
def api_sales_trend():
    cutoff = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    try:
        rows = execute_read_query_params(
            """
            SELECT transaction_date,
                   COALESCE(SUM(CASE WHEN type='Revenue' THEN amount END), 0) AS revenue,
                   COALESCE(SUM(CASE WHEN type='Expense' THEN amount END), 0) AS expenses
            FROM daily_transactions
            WHERE transaction_date >= %s
            GROUP BY transaction_date
            ORDER BY transaction_date
            """,
            (cutoff,),
        )
        return jsonify(
            {
                "labels": [r["transaction_date"].isoformat() for r in rows],
                "revenue": [float(r["revenue"]) for r in rows],
                "expenses": [float(r["expenses"]) for r in rows],
            }
        )
    except Exception as exc:
        return internal_error_response(exc)


@app.route("/api/dashboard/transactions-by-category", methods=["GET", "OPTIONS"])
def api_transactions_by_category():
    cutoff = (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%d")
    try:
        rows = execute_read_query_params(
            """
            SELECT category, COUNT(*) AS cnt
            FROM daily_transactions
            WHERE transaction_date >= %s
            GROUP BY category
            ORDER BY cnt DESC
            """,
            (cutoff,),
        )
        return jsonify({"labels": [r["category"] or "Other" for r in rows], "data": [int(r["cnt"]) for r in rows]})
    except Exception as exc:
        return internal_error_response(exc)


@app.route("/api/dashboard/alerts-by-severity", methods=["GET", "OPTIONS"])
def api_alerts_by_severity():
    try:
        rows = execute_read_query_params(
            "SELECT severity, COUNT(*) AS cnt FROM alerts WHERE status='Active' GROUP BY severity"
        )
        return jsonify({"labels": [r["severity"] for r in rows], "data": [int(r["cnt"]) for r in rows]})
    except Exception as exc:
        return internal_error_response(exc)


@app.route("/api/dashboard/health-scores", methods=["GET", "OPTIONS"])
def api_health_scores():
    try:
        rows = execute_read_query_params(
            """
            SELECT bhs.overall_score, bhs.cash_score, bhs.profitability_score, bhs.growth_score,
                   bhs.cost_control_score, bhs.risk_score, b.business_name
            FROM business_health_scores bhs
            JOIN businesses b ON b.business_id = bhs.business_id
            ORDER BY bhs.calculated_at DESC
            LIMIT 5
            """
        )
        return jsonify(
            {
                "businesses": [r["business_name"] for r in rows],
                "scores": [
                    {
                        "name": r["business_name"],
                        "overall": float(r["overall_score"] or 0),
                        "cash": float(r["cash_score"] or 0),
                        "profitability": float(r["profitability_score"] or 0),
                        "growth": float(r["growth_score"] or 0),
                        "cost_control": float(r["cost_control_score"] or 0),
                        "risk": float(r["risk_score"] or 0),
                    }
                    for r in rows
                ],
            }
        )
    except Exception as exc:
        return internal_error_response(exc)


@app.route("/api/dashboard/top-products", methods=["GET", "OPTIONS"])
def api_top_products():
    try:
        rows = execute_read_query_params(
            "SELECT product_name, stock_quantity, selling_price, cost_price FROM products ORDER BY stock_quantity DESC LIMIT 10"
        )
        margin_amount = [float((r["selling_price"] or 0) - (r["cost_price"] or 0)) for r in rows]
        margin_pct = [
            round(((r["selling_price"] or 0) - (r["cost_price"] or 0)) / (r["selling_price"] or 1) * 100, 1)
            if r["selling_price"]
            else 0
            for r in rows
        ]
        return jsonify(
            {
                "labels": [r["product_name"] for r in rows],
                "stock": [int(r["stock_quantity"] or 0) for r in rows],
                "margin": margin_pct,
                "margin_amount": margin_amount,
                "margin_pct": margin_pct,
            }
        )
    except Exception as exc:
        return internal_error_response(exc)


@app.route("/api/dashboard/employee-stats", methods=["GET", "OPTIONS"])
def api_employee_stats():
    try:
        rows = execute_read_query_params(
            "SELECT status, COUNT(*) AS cnt, COALESCE(AVG(salary),0) AS avg_salary FROM employees GROUP BY status"
        )
        return jsonify(
            {
                "labels": [r["status"] for r in rows],
                "counts": [int(r["cnt"]) for r in rows],
                "avg_salary": [round(float(r["avg_salary"]), 2) for r in rows],
            }
        )
    except Exception as exc:
        return internal_error_response(exc)


@app.route("/api/dashboard/recent-transactions", methods=["GET", "OPTIONS"])
def api_recent_transactions():
    limit = request.args.get("limit", 20, type=int)
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    try:
        base_sql = """
            SELECT transaction_id, transaction_date, type, category, amount, description
            FROM daily_transactions
            WHERE 1=1
        """
        params: list[Any] = []
        if search:
            base_sql += " AND (description ILIKE %s OR category ILIKE %s)"
            params.extend([f"%{search}%", f"%{search}%"])
        if category:
            base_sql += " AND category = %s"
            params.append(category)
        base_sql += " ORDER BY transaction_date DESC, transaction_id DESC LIMIT %s"
        params.append(limit)
        rows = execute_read_query_params(base_sql, tuple(params))
        for r in rows:
            r["amount"] = float(r["amount"] or 0)
            if r.get("transaction_date"):
                r["transaction_date"] = r["transaction_date"].isoformat()
        return jsonify({"transactions": rows})
    except Exception as exc:
        return internal_error_response(exc)


@app.route("/api/dashboard/sales-target", methods=["GET", "OPTIONS"])
def api_sales_target():
    try:
        rows = execute_read_query_params(
            """
            SELECT b.business_name, b.monthly_target_revenue,
                   COALESCE(SUM(CASE WHEN dt.type='Revenue' THEN dt.amount END), 0) AS current_revenue
            FROM businesses b
            LEFT JOIN daily_transactions dt ON dt.business_id = b.business_id
                AND EXTRACT(MONTH FROM dt.transaction_date) = EXTRACT(MONTH FROM CURRENT_DATE)
                AND EXTRACT(YEAR FROM dt.transaction_date) = EXTRACT(YEAR FROM CURRENT_DATE)
            GROUP BY b.business_id, b.business_name, b.monthly_target_revenue
            ORDER BY current_revenue DESC
            LIMIT 1
            """
        )
        if not rows:
            return jsonify({"current_revenue": 0, "target_revenue": 100000, "percentage": 0})
        row = rows[0]
        target = float(row["monthly_target_revenue"] or 100000)
        current = float(row["current_revenue"] or 0)
        pct = round((current / target * 100), 1) if target > 0 else 0
        return jsonify(
            {
                "business_name": row["business_name"],
                "current_revenue": current,
                "target_revenue": target,
                "percentage": pct,
            }
        )
    except Exception as exc:
        return internal_error_response(exc)


@app.route("/api/dashboard/categories", methods=["GET", "OPTIONS"])
def api_categories():
    try:
        rows = execute_read_query_params("SELECT DISTINCT category FROM daily_transactions ORDER BY category")
        return jsonify({"categories": [r["category"] for r in rows if r["category"]]})
    except Exception as exc:
        return internal_error_response(exc)


@app.route("/api/dashboard/business-info", methods=["GET", "OPTIONS"])
def get_business_info():
    conn = get_db_connection()
    try:
        import psycopg2.extras

        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM public.businesses ORDER BY created_at DESC LIMIT 1")
        business = cur.fetchone()
        if not business:
            return jsonify({"error": "No business found"}), 404
        return jsonify(business)
    except Exception as exc:
        return internal_error_response(exc)
    finally:
        conn.close()


if __name__ == "__main__":
    logger.info("Starting Flask development server.")
    app.run(host="0.0.0.0", port=5000, debug=True)
from flask import Flask, request, jsonify, Response, stream_with_context, g
from flask_cors import CORS
import os
import sqlite3
import time
import json
import uuid
import numpy as np
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv

# Database & AI Imports
from db_config import get_db_connection, execute_read_query_params
from transaction_import import parse_csv_bytes, parse_xlsx_bytes
from ocr_processor import extract_transactions_from_image
from langchain_openai import ChatOpenAI

# Chatbot/LangGraph Imports
from nodes import intent_detection, format_response
from intents.general_information_graph.subgraph import general_information_graph_workflow
from intents.database_request_graph.subgraph import database_request_graph_workflow
from intents.logs_request_graph.subgraph import logs_request_graph_workflow
from intents.metrics_request_graph.subgraph import metrics_request_graph_workflow
from langgraph.types import Command

from logger.logger import logger
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST, REGISTRY

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB
CORS(app)

# Constants & AI Clients
CHAT_DB_PATH = os.getenv("CHAT_DB_PATH", "chat_history.db")
groq_llm = ChatOpenAI(
    model_name="llama3-70b-8192",
    openai_api_key=os.getenv("GROQ_API_KEY"),
    openai_api_base="https://api.groq.com/openai/v1"
)

# --- SQLite Chat History Setup ---
def _get_chat_db():
    if "chat_db" not in g:
        g.chat_db = sqlite3.connect(CHAT_DB_PATH)
        g.chat_db.row_factory = sqlite3.Row
    return g.chat_db

def _init_chat_db():
    db = sqlite3.connect(CHAT_DB_PATH)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            conversation_id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT 'New Chat',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user','assistant')),
            content TEXT NOT NULL,
            intent TEXT DEFAULT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
        );
    """)
    db.close()

# --- Helper Functions (From Kushal-Dev) ---
def get_period_dates(period):
    now = datetime.utcnow()
    y, m = now.year, now.month
    if period == "this_month":
        return datetime(y, m, 1).strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d")
    if period == "last_month":
        last_day_prev = datetime(y, m, 1) - timedelta(days=1)
        return datetime(last_day_prev.year, last_day_prev.month, 1).strftime("%Y-%m-%d"), last_day_prev.strftime("%Y-%m-%d")
    if period == "ytd":
        return datetime(y, 1, 1).strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d")
    start = now - timedelta(days=30)
    return start.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d")

def get_latest_business_id():
    res = execute_read_query_params("SELECT business_id FROM businesses ORDER BY created_at DESC LIMIT 1")
    return res[0]["business_id"] if res else None

# --- Dashboard API Endpoints ---

@app.route("/api/dashboard/summary-sql", methods=["GET"])
def api_dashboard_summary():
    period = request.args.get("period", "this_month")
    start_date, end_date = get_period_dates(period)
    bid = get_latest_business_id()
    if not bid: return jsonify({"error": "No business found"}), 404
    
    txn = execute_read_query_params("""
        SELECT 
            COALESCE(SUM(CASE WHEN type='Revenue' THEN amount END), 0) AS total_revenue,
            COALESCE(SUM(CASE WHEN type='Expense' THEN amount END), 0) AS total_expenses,
            COUNT(*) AS total_transactions
        FROM daily_transactions WHERE business_id = %s AND transaction_date BETWEEN %s AND %s
    """, (bid, start_date, end_date))

    alerts = execute_read_query_params("SELECT COUNT(*) AS active_alerts FROM alerts WHERE business_id = %s AND status = 'Active'", (bid,))

    curr = txn[0] if txn else {}

    # Parse dates to compute prev period
    dt_start = datetime.strptime(start_date, "%Y-%m-%d").date()
    if period == "this_month":
        p_start = (dt_start - timedelta(days=1)).replace(day=1)
        p_end = dt_start - timedelta(days=1)
    elif period in ("last_7_days", "last_7"):
        p_start = dt_start - timedelta(days=7)
        p_end = dt_start - timedelta(days=1)
    else:
        p_start = dt_start - timedelta(days=30)
        p_end = dt_start - timedelta(days=1)

    p_start_str = p_start.strftime("%Y-%m-%d")
    p_end_str = p_end.strftime("%Y-%m-%d")

    prev_txn = execute_read_query_params("""
        SELECT
            COALESCE(SUM(CASE WHEN type='Revenue' THEN amount END), 0) AS total_revenue,
            COALESCE(SUM(CASE WHEN type='Expense' THEN amount END), 0) AS total_expenses
        FROM daily_transactions WHERE business_id = %s AND transaction_date BETWEEN %s AND %s
    """, (bid, p_start_str, p_end_str))

    prev = prev_txn[0] if prev_txn else {}

    def calc_change(curr_val, prev_val):
        if not prev_val: return 100.0 if curr_val else 0.0
        return round(((curr_val - prev_val) / prev_val) * 100.0, 1)

    rev = float(curr.get("total_revenue", 0))
    exp = float(curr.get("total_expenses", 0))
    prev_rev = float(prev.get("total_revenue", 0))
    prev_exp = float(prev.get("total_expenses", 0))

    return jsonify({
        "total_revenue": rev,
        "total_expenses": exp,
        "net_profit": rev - exp,
        "total_transactions": int(curr.get("total_transactions", 0)),
        "active_alerts": int(alerts[0].get("active_alerts", 0)) if alerts else 0,
        "revenue_change": calc_change(rev, prev_rev),
        "expenses_change": calc_change(exp, prev_exp)
    })

@app.route("/api/dashboard/forecast", methods=["GET"])
def api_forecast():
    bid = get_latest_business_id()
    if not bid: return jsonify({"historical":[], "forecast":[]}), 404
    try:
        cutoff = (datetime.utcnow() - timedelta(days=60)).strftime("%Y-%m-%d")
        rows = execute_read_query_params("""
            SELECT transaction_date, SUM(amount) as amount FROM daily_transactions 
            WHERE business_id = %s AND type='Revenue' AND transaction_date >= %s 
            GROUP BY 1 ORDER BY 1
        """, (bid, cutoff))
        
        hist = [{"date": r["transaction_date"].strftime("%Y-%m-%d"), "actual": float(r["amount"])} for r in rows]
        # Basic prediction logic using numpy
        x = np.arange(len(hist))
        y = np.array([h["actual"] for h in hist])
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        
        forecast = []
        last_date = datetime.strptime(hist[-1]["date"], "%Y-%m-%d") if hist else datetime.utcnow()
        for i in range(1, 31):
            forecast.append({
                "date": (last_date + timedelta(days=i)).strftime("%Y-%m-%d"),
                "predicted": max(0, round(float(p(len(hist) + i)), 2))
            })
        
        return jsonify({"historical": hist, "forecast": forecast, "insight": "Revenue is trending upwards based on last 60 days."})
    except Exception as e:
        return internal_error_response(e)

@app.route("/api/v1/onboarding", methods=["POST"])
def onboarding():
    data = request.json
    business_name = data.get("business_name")
    email = data.get("email", "").lower().strip()
    if not business_name or not email: return jsonify({"error": "Missing fields"}), 400
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        bid = str(uuid.uuid4())
        cur.execute("INSERT INTO businesses (business_id, business_name, industry_type, owner_name) VALUES (%s, %s, %s, %s)", 
                   (bid, business_name, data.get("business_category"), data.get("full_name")))
        cur.execute("INSERT INTO users (business_id, name, email, password_hash) VALUES (%s, %s, %s, %s)",
                   (bid, data.get("full_name"), email, SOCIAL_LOGIN_PASSWORD_HASH))
        conn.commit()
        return jsonify({"success": True, "business_id": bid}), 201
    finally:
        conn.close()

# --- SSE Chat Logic ---
def iter_query_sse(input_query, thread_id):
    # LangGraph logic from testsparkhack branch
    yield f"data: {json.dumps({'type': 'status', 'status': 'Thinking...'})}\n\n"
    intent = intent_detection.detect_intent(input_query)
    # Stream tokens here... (Simplified for merge, use your full _stream_graph logic)
    yield f"data: {json.dumps({'type': 'token', 'content': 'AI Response placeholder...'})}\n\n"
    yield f"data: {json.dumps({'type': 'final', 'intent_str': 'database_request'})}\n\n"

@app.route("/api/chat/send", methods=["POST"])
def api_chat_send():
    data = request.json
    conv_id = data.get("conversation_id")
    msg = data.get("message")
    # Wrap iter_query_sse in SSE Response
    return Response(stream_with_context(iter_query_sse(msg, conv_id)), mimetype="text/event-stream")

# Start Server
_init_chat_db()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
