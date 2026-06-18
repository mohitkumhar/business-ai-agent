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

from api_errors import SAFE_INTERNAL_ERROR_MESSAGE, internal_error_response
from db_config import execute_read_query_params, get_db_connection
from auth_passwords import SOCIAL_LOGIN_PASSWORD_HASH
from llm.base_llm import base_llm
from logger.logger import logger
from request_ids import get_request_id
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
        if request.method == "OPTIONS":
            return jsonify({}), 200
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
    g.request_id = get_request_id(request.headers.get("X-Request-ID"), getattr(g, "request_id", None))


@app.after_request
def _record_metrics(response):
    if request.path == "/metrics":
        return response
    latency = time.time() - getattr(g, "start_time", time.time())
    endpoint = request.endpoint or "unknown"
    AGENT_REQUEST_COUNT.labels(request.method, endpoint, response.status_code).inc()
    AGENT_REQUEST_LATENCY.labels(request.method, endpoint).observe(latency)
    response.headers["X-Request-ID"] = get_request_id(getattr(g, "request_id", None))
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

_whatsapp_tables_initialized = False

def _initialize_whatsapp_tables_safe():
    global _whatsapp_tables_initialized

    if _whatsapp_tables_initialized:
        return

    try:
        _ensure_whatsapp_tables()
        _whatsapp_tables_initialized = True
        logger.info("WhatsApp tables initialized successfully.")
    except Exception as exc:
        logger.warning(
            "WhatsApp table initialization failed: %s",
            exc
        )


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


