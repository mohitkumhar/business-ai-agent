from __future__ import annotations
from typing import Any
import csv
import io
from flask import Flask, request, jsonify, Response, stream_with_context, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import psycopg2.extras
import requests
import sqlite3
import time
import json
import uuid
import jwt
import bcrypt
import hashlib
from functools import wraps
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
from query_execution import stream_agent_sse_lines
from auth import AuthError, decode_jwt_identity, require_jwt_secret
from api_errors import internal_error_response
from auth_passwords import SOCIAL_LOGIN_PASSWORD_HASH, verify_password
from swagger_docs import register_swagger_docs

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB
app.config["SECRET_KEY"] = require_jwt_secret(os.getenv("JWT_SECRET"))
CORS(app)

DEFAULT_RATE_LIMITS = [
    limit.strip()
    for limit in os.getenv("RATE_LIMIT_DEFAULT", "200 per day;50 per hour").split(";")
    if limit.strip()
]
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=DEFAULT_RATE_LIMITS,
    headers_enabled=True,
)
AUTH_RATE_LIMIT = os.getenv("RATE_LIMIT_AUTH", "5 per minute")
CHAT_RATE_LIMIT = os.getenv("RATE_LIMIT_CHAT", "10 per minute")
IMPORT_RATE_LIMIT = os.getenv("RATE_LIMIT_IMPORT", "20 per hour")

# --- Authentication Logic ---
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

@app.route("/api/auth/signup", methods=["POST"])
@limiter.limit(AUTH_RATE_LIMIT)
def auth_signup():
    data = request.json
    email = data.get("email", "").lower().strip()
    password = data.get("password")
    name = data.get("name")
    biz_name = data.get("business_name")

    if not all([email, password, name, biz_name]):
        return jsonify({"message": "All fields are required"}), 400

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Check if user exists
        cur.execute("SELECT user_id FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            return jsonify({"message": "User already exists"}), 409

        # Create business first
        biz_id = str(uuid.uuid4())
        cur.execute("INSERT INTO businesses (business_id, business_name, industry_type, owner_name) VALUES (%s, %s, %s, %s)",
                   (biz_id, biz_name, data.get("industry", "Other"), name))
        
        # Hash password and create user
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        cur.execute("INSERT INTO users (business_id, name, email, password_hash) VALUES (%s, %s, %s, %s) RETURNING user_id",
                   (biz_id, name, email, hashed))
        user_id = cur.fetchone()[0]
        conn.commit()

        token = jwt.encode({
            "user_id": user_id,
            "business_id": biz_id,
            "exp": datetime.utcnow() + timedelta(days=7)
        }, app.config["SECRET_KEY"], algorithm="HS256")

        return jsonify({"token": token, "business_id": biz_id, "user": {"name": name, "email": email}}), 201
    except Exception as e:
        return internal_error_response(e, field="message")
    finally:
        conn.close()

@app.route("/api/auth/login", methods=["POST"])
@limiter.limit(AUTH_RATE_LIMIT)
def auth_login():
    data = request.json
    email = data.get("email", "").lower().strip()
    password = data.get("password")

    if not all([email, password]):
        return jsonify({"message": "Email and password required"}), 400

    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT user_id, business_id, name, password_hash FROM users WHERE email = %s", (email,))
        user = cur.fetchone()

        if not user or not verify_password(password, user.get("password_hash")):
            return jsonify({"message": "Invalid email or password"}), 401

        token = jwt.encode({
            "user_id": user["user_id"],
            "business_id": user["business_id"],
            "exp": datetime.utcnow() + timedelta(days=7)
        }, app.config["SECRET_KEY"], algorithm="HS256")

        return jsonify({"token": token, "business_id": user["business_id"], "user": {"name": user["name"], "email": email}}), 200
    except Exception as e:
        return internal_error_response(e, field="message")
    finally:
        conn.close()

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST, REGISTRY

# --- Configurations ---
WHATSAPP_VERIFY_TOKEN = (os.getenv("WHATSAPP_VERIFY_TOKEN") or "").strip()
WHATSAPP_ACCESS_TOKEN = (os.getenv("WHATSAPP_ACCESS_TOKEN") or "").strip()
WHATSAPP_PHONE_NUMBER_ID = (os.getenv("WHATSAPP_PHONE_NUMBER_ID") or "").strip()
TELEGRAM_BOT_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
DEFAULT_BUSINESS_ID = (os.getenv("DEFAULT_BUSINESS_ID") or "").strip()

# --- Metrics ---
AGENT_REQUEST_COUNT = Counter("agent_requests_total", "Total requests", ["method", "endpoint", "status"])
AGENT_REQUEST_LATENCY = Histogram("agent_request_duration_seconds", "Request latency", ["method", "endpoint"])
AGENT_INTENT_COUNT = Counter("agent_intent_detections_total", "Intent detections", ["intent"])

# Constants & AI Clients
CHAT_DB_PATH = os.getenv("CHAT_DB_PATH", "chat_history.db")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
if not GROQ_API_KEY:
    logger.warning("GROQ_API_KEY is not set. Groq-powered responses will fail until it is configured.")

groq_llm = ChatOpenAI(
    model_name="llama3-70b-8192",
    openai_api_key=GROQ_API_KEY or "dummy_key_to_prevent_startup_crash",
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
def _ensure_whatsapp_tables():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.whatsapp_contacts (
                    phone TEXT PRIMARY KEY,
                    business_id UUID NOT NULL REFERENCES public.businesses(business_id) ON DELETE CASCADE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
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
            """)
        conn.commit()
    finally:
        conn.close()
# --- External Integration Helpers (WhatsApp/Telegram) ---
def _download_whatsapp_media(media_id: str) -> tuple[bytes, str]:
    if not WHATSAPP_ACCESS_TOKEN: raise ValueError("WhatsApp token missing")
    meta = requests.get(f"https://graph.facebook.com/v21.0/{media_id}", headers={"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}).json()
    url = meta.get("url")
    if not url: raise ValueError("Media URL missing")
    blob = requests.get(url, headers={"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"})
    return blob.content, meta.get("mime_type", "image/jpeg")

def _extract_bill_data_from_image(image_bytes: bytes, mime_type: str) -> dict[str, Any]:
    extension_by_mime = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }
    filename = f"whatsapp-bill{extension_by_mime.get(mime_type.lower(), '.jpg')}"
    transactions = extract_transactions_from_image(image_bytes, filename)
    if not transactions:
        raise ValueError("No bill transaction could be extracted from the image.")

    transaction_date, tx_type, category, amount, description = transactions[0]
    return {
        "date": transaction_date,
        "amount": amount,
        "category": category,
        "type": tx_type,
        "vendor": description or "Unknown",
    }
def _normalize_bill_fields(extracted: dict[str, Any]) -> dict[str, Any]:
    amount = extracted.get("amount")
    try:
        amount = float(amount) if amount is not None else 0.0
    except (ValueError, TypeError):
        amount = 0.0
    tx_date = str(
        extracted.get("transaction_date")
        or extracted.get("date")
        or datetime.utcnow().date().isoformat()
    )
    ttype = str(extracted.get("type") or "Expense").strip().lower()
    if ttype not in ("revenue", "expense"):
        ttype = "expense"
    category = str(
        extracted.get("category")
        or extracted.get("vendor_name")
        or extracted.get("vendor")
        or "Uncategorized"
    )
    description = str(
        extracted.get("description")
        or extracted.get("vendor_name")
        or extracted.get("vendor")
        or "Bill ingestion"
    )
    return {
        "amount": max(amount, 0.0),
        "transaction_date": tx_date,
        "type": "Revenue" if ttype == "revenue" else "Expense",
        "category": category[:100],
        "description": description,
        "vendor_name": str(extracted.get("vendor_name") or "").strip(),
        "confidence": extracted.get("confidence", None),
    }
def _send_whatsapp_text(to_number: str, text: str):
    if not (WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID):
        logger.warning("WhatsApp send skipped; credentials not configured.")
        return

    body = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": text[:4096]
        },
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
    res = groq_llm.invoke(prompt)
    return res.content if isinstance(res.content, str) else json.dumps(res.content)

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
    res = groq_llm.invoke(prompt)
    return res.content if isinstance(res.content, str) else json.dumps(res.content)

def _run_agent_to_text(query: str, thread_id: str, business_id: str) -> str:
    chunks: list[str] = []
    fallback_error = None

    for line in stream_agent_sse_lines(query, thread_id, business_id):
        if not line.startswith("data: "):
            continue

        payload = line[6:].strip()
        if not payload:
            continue

        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            continue

        if event.get("type") == "token":
            chunks.append(event.get("content", ""))
        elif event.get("type") == "error":
            fallback_error = event.get("error")

    response = "".join(chunks).strip()
    if response:
        return response
    if fallback_error:
        return f"Sorry, I hit an error: {fallback_error}"
    return "I could not generate a response."

def _send_telegram_text(chat_id: int, text: str) -> None:
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram send skipped; TELEGRAM_BOT_TOKEN is not configured.")
        return

    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text[:4096]},
        timeout=30,
    ).raise_for_status()

# --- Helper Functions (From Kushal-Dev) ---
def get_period_dates(period):
    end_date = date.today()
    if period == "this_month":
        start_date = end_date.replace(day=1)
    elif period == "last_month":
        last_month_end = end_date.replace(day=1) - timedelta(days=1)
        start_date = last_month_end.replace(day=1)
        end_date = last_month_end
    elif period == "last_7_days":
        start_date = end_date - timedelta(days=7)
    elif period == "last_30_days":
        start_date = end_date - timedelta(days=30)
    elif period == "ytd":
        start_date = date(end_date.year, 1, 1)
    else:
        start_date = end_date - timedelta(days=30)
    return start_date, end_date

def _sse_stream_response(generator):
    response = Response(stream_with_context(generator), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache, no-transform"
    response.headers["X-Accel-Buffering"] = "no"
    response.headers["Connection"] = "keep-alive"
    return response


# --- Dashboard API Endpoints ---

@app.route("/")
def home():
    return jsonify({"status": "healthy", "service": "ProfitPilot Backend", "version": "1.0.0"})

@app.route("/api/dashboard/forecast", methods=["GET"])
@token_required
def api_forecast():
    bid = get_current_business_id()
    if not bid: return jsonify({"historical":[], "forecast":[], "trend_direction": "flat", "trend_percent": 0}), 404
    try:
        cutoff = (datetime.utcnow() - timedelta(days=60)).strftime("%Y-%m-%d")
        rows = execute_read_query_params("""
            SELECT transaction_date, SUM(amount) as amount FROM daily_transactions 
            WHERE business_id = %s AND type='Revenue' AND transaction_date >= %s 
            GROUP BY 1 ORDER BY 1
        """, (bid, cutoff))
        
        hist = [{"date": r["transaction_date"].strftime("%Y-%m-%d"), "actual": float(r["amount"])} for r in rows]
        
        if not hist:
            return jsonify({
                "historical": [], 
                "forecast": [], 
                "trend_direction": "flat", 
                "trend_percent": 0,
                "insight": "No revenue data available for forecasting yet."
            })

        # Basic prediction logic using numpy
        x = np.arange(len(hist))
        y = np.array([h["actual"] for h in hist])
        
        if len(hist) > 1:
            z = np.polyfit(x, y, 1)
            p = np.poly1d(z)
            trend = "up" if z[0] > 0 else "down"
            percent = abs(round(float(z[0] / (np.mean(y) or 1) * 100), 1))
        else:
            p = lambda val: y[0] if len(y) > 0 else 0
            trend = "flat"
            percent = 0
            
        forecast = []
        last_date = datetime.strptime(hist[-1]["date"], "%Y-%m-%d")
        for i in range(1, 31):
            forecast.append({
                "date": (last_date + timedelta(days=i)).strftime("%Y-%m-%d"),
                "predicted": max(0, round(float(p(len(hist) + i)), 2))
            })
        
        return jsonify({
            "historical": hist, 
            "forecast": forecast, 
            "trend_direction": trend,
            "trend_percent": percent,
            "insight": f"Revenue is trending {trend}wards based on the last {len(hist)} days of data."
        })
    except Exception as e:
        return internal_error_response(e)

@app.route("/api/dashboard/categories", methods=["GET", "OPTIONS"])
@token_required
def api_categories():
    bid = get_current_business_id()
    try:
        rows = execute_read_query_params(
            "SELECT DISTINCT category FROM daily_transactions "
            "WHERE business_id = %s AND category IS NOT NULL ORDER BY category",
            (bid,),
        )
        return jsonify({"categories": [r["category"] for r in rows]})
    except Exception as exc:
        return internal_error_response(exc)

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
        message = update.get("message") or update.get("edited_message") or {}
        chat_id = (message.get("chat") or {}).get("id")

        if chat_id is None:
            return jsonify({"ok": True})

        text = (message.get("text") or message.get("caption") or "").strip()
        has_attachment = bool(message.get("photo") or message.get("document") or message.get("voice"))

        if not text:
            reply = (
                "I received your attachment, but this Telegram webhook currently supports text prompts "
                "and captions. Please send a question or add a caption so I can help."
            ) if has_attachment else "Please send a text question so I can help."
            _send_telegram_text(chat_id, reply)
            return jsonify({"ok": True})

        business_id = DEFAULT_BUSINESS_ID or "550e8400-e29b-41d4-a716-446655440000"
        answer = _run_agent_to_text(text, f"tg-{chat_id}", business_id)
        _send_telegram_text(chat_id, answer)
        return jsonify({"ok": True})
    except Exception as e:
        logger.error("Telegram webhook failed: %s", e, exc_info=True)
        try:
            update = request.get_json(silent=True) or {}
            message = update.get("message") or update.get("edited_message") or {}
            chat_id = (message.get("chat") or {}).get("id")
            if chat_id is not None:
                _send_telegram_text(chat_id, "Sorry, I could not process that Telegram update.")
        except Exception:
            pass
        return internal_error_response(e)
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

# --- Transaction Import Endpoints ---

@app.route("/api/v1/import/transactions", methods=["POST"])
@limiter.limit(IMPORT_RATE_LIMIT)
@token_required
def import_transactions():
    if "file" not in request.files: return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    bid = get_current_business_id()
    try:
        content = file.read()
        filename = file.filename.lower()
        if filename.endswith(".csv"): rows = parse_csv_bytes(content)
        elif filename.endswith(".xlsx"): rows = parse_xlsx_bytes(content)
        else: return jsonify({"error": "Unsupported file format"}), 400
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                for row in rows:
                    cur.execute("""
                        INSERT INTO daily_transactions (business_id, transaction_date, type, category, amount, description)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (bid, *row))
            conn.commit()
            return jsonify({"message": f"Successfully imported {len(rows)} transactions!"}), 201
        finally: conn.close()
    except Exception as e:
        logger.error(f"Import failed: {str(e)}", exc_info=True)
        return internal_error_response(e)

@app.route("/api/v1/import/notebook", methods=["POST"])
@limiter.limit(IMPORT_RATE_LIMIT)
@token_required
def import_notebook():
    if "file" not in request.files: return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    bid = get_current_business_id()
    try:
        content = file.read()
        filename = file.filename
        
        # MD5 Hash Check
        file_hash = hashlib.md5(content).hexdigest()
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Check if this hash was already imported for this business
                cur.execute("SELECT 1 FROM daily_transactions WHERE business_id = %s AND description LIKE %s LIMIT 1", 
                           (bid, f"%[Import Hash: {file_hash}]%"))
                if cur.fetchone():
                    return jsonify({"error": "This notebook page has already been imported."}), 409
        finally: conn.close()

        # Use OCR Processor
        rows = extract_transactions_from_image(content, filename)
        
        # Return for PREVIEW first (Requirement #5)
        return jsonify({
            "transactions": [
                {
                    "date": r[0].strftime("%Y-%m-%d"),
                    "type": r[1],
                    "category": r[2],
                    "amount": r[3],
                    "description": r[4],
                    "hash": file_hash
                } for r in rows
            ],
            "hash": file_hash
        }), 200
        
    except Exception as e:
        logger.error(f"Notebook extraction failed: {str(e)}", exc_info=True)
        return internal_error_response(e)

@app.route("/api/v1/import/confirm-notebook", methods=["POST"])
@limiter.limit(IMPORT_RATE_LIMIT)
@token_required
def confirm_notebook():
    data = request.json
    bid = get_current_business_id()
    transactions = data.get("transactions", [])
    file_hash = data.get("hash")
    
    if not transactions:
        return jsonify({"error": "No transactions to confirm"}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            for tx in transactions:
                # We append the hash to the description to prevent duplicates in the future (Requirement #4)
                desc = f"{tx.get('description', '')} [Import Hash: {file_hash}]"
                cur.execute("""
                    INSERT INTO daily_transactions (business_id, transaction_date, type, category, amount, description)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (bid, tx["date"], tx["type"], tx["category"], tx["amount"], desc))
        conn.commit()
        return jsonify({"message": f"Successfully saved {len(transactions)} transactions!"}), 201
    except Exception as e:
        return internal_error_response(e)
    finally:
        conn.close()

# --- AI Chat API ---

@app.route("/api/v1/query", methods=["POST", "GET"])
@limiter.limit(CHAT_RATE_LIMIT)
def query_agent():
    input_query = request.args.get("input-query", "")
    thread_id = request.args.get("thread-id", "")
    business_id = request.args.get("business-id", "")

    if not input_query:
        return jsonify({"is_error": True, "error": "input query is required"}), 400
    if not thread_id:
        return jsonify({"is_error": True, "error": "thread-id is required"}), 400

    return _sse_stream_response(
        stream_agent_sse_lines(
            input_query,
            thread_id,
            business_id,
            on_chain_intent=lambda name: AGENT_INTENT_COUNT.labels(name).inc(),
        )
    )


@app.route("/api/chat/send", methods=["POST"])
@limiter.limit(CHAT_RATE_LIMIT)
@token_required
def api_chat_send():
    data = request.json
    msg = data.get("message")
    conv_id = data.get("conversation_id") or str(uuid.uuid4())
    bid = get_current_business_id()
    return Response(stream_with_context(stream_agent_sse_lines(msg, conv_id, bid)), mimetype="text/event-stream")

@app.route("/api/dashboard/financial-overview", methods=["GET", "OPTIONS"])
@token_required
def api_financial_overview():
    bid = get_current_business_id()
    try:
        rows = execute_read_query_params("""
            SELECT year, month, 
                   COALESCE(SUM(total_revenue),0) AS total_revenue, 
                   COALESCE(SUM(total_expenses),0) AS total_expenses,
                   COALESCE(SUM(net_profit),0) AS net_profit,
                   COALESCE(SUM(cash_balance),0) AS cash_balance
            FROM financial_records
            WHERE business_id = %s
            GROUP BY year, month
            ORDER BY year DESC, month DESC
            LIMIT 12
        """, (bid,))
        rows = list(rows)
        rows.reverse()
        labels = [f"{r['year']}-{str(r['month']).zfill(2)}" for r in rows]
        return jsonify({
            "labels": labels,
            "revenue": [float(r["total_revenue"]) for r in rows],
            "expenses": [float(r["total_expenses"]) for r in rows],
            "net_profit": [float(r["net_profit"]) for r in rows],
            "cash_balance": [float(r["cash_balance"]) for r in rows]
        })
    except Exception as exc:
        return internal_error_response(exc)

@app.route("/api/dashboard/revenue-vs-expense", methods=["GET", "OPTIONS"])
@token_required
def api_revenue_vs_expense():
    bid = get_current_business_id()
    period = request.args.get("period", "this_month")
    start_date, end_date = get_period_dates(period)
    try:
        rows = execute_read_query_params("""
            SELECT category, type, COALESCE(SUM(amount), 0) AS total
            FROM daily_transactions
            WHERE business_id = %s AND transaction_date BETWEEN %s AND %s
            GROUP BY category, type
            ORDER BY total DESC
        """, (bid, start_date, end_date))
        
        revenue_cats = {}
        expense_cats = {}
        for r in rows:
            cat = r["category"] or "Other"
            amt = float(r["total"])
            if r["type"] == "Revenue":
                revenue_cats[cat] = revenue_cats.get(cat, 0) + amt
            else:
                expense_cats[cat] = expense_cats.get(cat, 0) + amt
                
        labels = sorted(set(list(revenue_cats.keys()) + list(expense_cats.keys())))
        return jsonify({
            "labels": labels,
            "revenue": [revenue_cats.get(c, 0) for c in labels],
            "expenses": [expense_cats.get(c, 0) for c in labels]
        })
    except Exception as exc:
        return internal_error_response(exc)

@app.route("/api/dashboard/sales-trend", methods=["GET", "OPTIONS"])
@token_required
def api_sales_trend():
    bid = get_current_business_id()
    period = request.args.get("period", "this_month")
    start_date, end_date = get_period_dates(period)
    try:
        rows = execute_read_query_params("""
            SELECT transaction_date, 
                   COALESCE(SUM(CASE WHEN type='Revenue' THEN amount END), 0) AS revenue,
                   COALESCE(SUM(CASE WHEN type='Expense' THEN amount END), 0) AS expenses
            FROM daily_transactions
            WHERE business_id = %s AND transaction_date BETWEEN %s AND %s
            GROUP BY transaction_date
            ORDER BY transaction_date
        """, (bid, start_date, end_date))
        return jsonify({
            "labels": [r["transaction_date"].strftime("%Y-%m-%d") for r in rows],
            "revenue": [float(r["revenue"]) for r in rows],
            "expenses": [float(r["expenses"]) for r in rows]
        })
    except Exception as exc:
        return internal_error_response(exc)

@app.route("/api/dashboard/recent-transactions", methods=["GET", "OPTIONS"])
@token_required
def api_recent_transactions():
    bid = get_current_business_id()
    limit = request.args.get("limit", 20, type=int)
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    try:
        sql = "SELECT transaction_id, transaction_date, type, category, amount, description FROM daily_transactions WHERE business_id = %s"
        params = [bid]
        if search:
            sql += " AND (description ILIKE %s OR category ILIKE %s)"
            params.extend([f"%{search}%", f"%{search}%"])
        if category:
            sql += " AND category = %s"
            params.append(category)
        sql += " ORDER BY transaction_date DESC LIMIT %s"
        params.append(limit)
        
        rows = execute_read_query_params(sql, tuple(params))
        for r in rows:
            r["amount"] = float(r["amount"] or 0)
            r["transaction_date"] = r["transaction_date"].strftime("%Y-%m-%d")
        return jsonify({"transactions": rows})
    except Exception as exc:
        return internal_error_response(exc)

@app.route("/api/dashboard/export-csv", methods=["GET", "OPTIONS"])
@token_required
def api_export_dashboard_csv():
    try:
        bid = get_current_business_id()
        period = request.args.get("period", "this_month")
        start_date, end_date = get_period_dates(period)
        rows = execute_read_query_params("""
            SELECT transaction_id, transaction_date, type, category, amount, description
            FROM daily_transactions
            WHERE business_id = %s AND transaction_date BETWEEN %s AND %s
            ORDER BY transaction_date DESC, transaction_id DESC
        """, (bid, start_date, end_date))

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["transaction_id", "transaction_date", "type", "category", "amount", "description"])
        for row in rows:
            transaction_date = row["transaction_date"]
            if hasattr(transaction_date, "strftime"):
                transaction_date = transaction_date.strftime("%Y-%m-%d")
            writer.writerow([
                row["transaction_id"],
                transaction_date,
                row["type"],
                row["category"],
                row["amount"] or 0,
                row["description"],
            ])

        filename = f"profitpilot_export_{period}_{date.today().isoformat()}.csv"
        response = Response(output.getvalue(), mimetype="text/csv")
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        return response
    except Exception as exc:
        return internal_error_response(exc)

@app.route("/api/dashboard/summary-sql", methods=["GET", "OPTIONS"])
@token_required
def api_dashboard_summary():
    bid = get_current_business_id()
    period = request.args.get("period", "this_month")
    start_date, end_date = get_period_dates(period)
    
    # Prev period for growth
    if period == "this_month":
        p_start = (start_date - timedelta(days=1)).replace(day=1)
        p_end = start_date - timedelta(days=1)
    elif period == "last_7_days":
        p_start = start_date - timedelta(days=7)
        p_end = start_date - timedelta(days=1)
    else:
        p_start = start_date - timedelta(days=30)
        p_end = start_date - timedelta(days=1)

    try:
        def get_metrics(s, e):
            r = execute_read_query_params("""
                SELECT 
                    COALESCE(SUM(CASE WHEN type='Revenue' THEN amount END), 0) AS rev,
                    COALESCE(SUM(CASE WHEN type='Expense' THEN amount END), 0) AS exp,
                    COUNT(*) AS txns
                FROM daily_transactions 
                WHERE business_id = %s AND transaction_date BETWEEN %s AND %s
            """, (bid, s, e))[0]
            alerts = execute_read_query_params("SELECT COUNT(*) FROM alerts WHERE business_id = %s AND status='Active'", (bid,))[0]["count"]
            return r["rev"], r["exp"], r["txns"], alerts

        rev, exp, txns, alerts = get_metrics(start_date, end_date)
        prev_rev, prev_exp, prev_txns, _ = get_metrics(p_start, p_end)

        def calc_change(curr, prev):
            if not prev: return 100 if curr else 0
            return round(((curr - prev) / prev) * 100, 1)

        return jsonify({
            "total_revenue": float(rev),
            "total_expenses": float(exp),
            "net_profit": float(rev - exp),
            "total_transactions": int(txns),
            "active_alerts": int(alerts),
            "revenue_change": calc_change(rev, prev_rev),
            "expenses_change": calc_change(exp, prev_exp),
            "net_profit_change": calc_change(rev - exp, prev_rev - prev_exp),
            "transactions_change": calc_change(txns, prev_txns),
        })
    except Exception as exc:
        return internal_error_response(exc)

@app.route("/api/dashboard/alerts-list", methods=["GET"])
@token_required
def api_alerts_list():
    bid = get_current_business_id()
    try:
        rows = execute_read_query_params("SELECT alert_id, message, severity, status, created_at FROM alerts WHERE business_id = %s ORDER BY created_at DESC LIMIT 50", (bid,))
        for r in rows:
            r["created_at"] = r["created_at"].strftime("%Y-%m-%d %H:%M")
        return jsonify({"alerts": rows})
    except Exception as exc:
        return internal_error_response(exc)

@app.route("/api/dashboard/business-info", methods=["GET", "OPTIONS"])
@token_required
def get_business_info():
    bid = get_current_business_id()
    if not bid: return jsonify({"error": "No business found"}), 404
    try:
        rows = execute_read_query_params("SELECT * FROM businesses WHERE business_id = %s", (bid,))
        return jsonify(rows[0] if rows else {})
    except Exception as exc:
        return internal_error_response(exc)

@app.route("/api/dashboard/sales-target", methods=["GET", "OPTIONS"])
@token_required
def api_sales_target():
    bid = get_current_business_id()
    if not bid: return jsonify({"current_revenue": 0, "target_revenue": 100000, "percentage": 0})
    try:
        rows = execute_read_query_params("""
            SELECT monthly_target_revenue, 
                   (SELECT COALESCE(SUM(amount), 0) FROM daily_transactions 
                    WHERE business_id = %s AND type='Revenue' 
                    AND EXTRACT(MONTH FROM transaction_date) = EXTRACT(MONTH FROM CURRENT_DATE)) as current_revenue
            FROM businesses WHERE business_id = %s
        """, (bid, bid))
        if not rows: return jsonify({"current_revenue": 0, "target_revenue": 100000, "percentage": 0})
        row = rows[0]
        target = float(row["monthly_target_revenue"] or 100000)
        current = float(row["current_revenue"] or 0)
        pct = round((current / target * 100), 1) if target > 0 else 0
        return jsonify({"current_revenue": current, "target_revenue": target, "percentage": pct})
    except Exception as exc:
        return internal_error_response(exc)

@app.route("/api/dashboard/alerts-by-severity", methods=["GET", "OPTIONS"])
@token_required
def api_alerts_by_severity():
    bid = get_current_business_id()
    try:
        rows = execute_read_query_params("SELECT severity, COUNT(*) AS cnt FROM alerts WHERE business_id = %s AND status='Active' GROUP BY severity", (bid,))
        return jsonify({"labels": [r["severity"] for r in rows], "data": [int(r["cnt"]) for r in rows]})
    except Exception as exc:
        return internal_error_response(exc)

@app.route("/api/dashboard/health-scores", methods=["GET", "OPTIONS"])
@token_required
def api_health_scores():
    bid = get_current_business_id()
    try:
        rows = execute_read_query_params("""
            SELECT bhs.overall_score, bhs.cash_score, bhs.profitability_score, bhs.growth_score,
                   bhs.cost_control_score, bhs.risk_score, b.business_name
            FROM business_health_scores bhs
            JOIN businesses b ON b.business_id = bhs.business_id
            WHERE b.business_id = %s
            ORDER BY bhs.calculated_at DESC
            LIMIT 5
        """, (bid,))
        
        if not rows:
            return jsonify({"businesses": [], "scores": []})
            
        return jsonify({
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
        })
    except Exception as exc:
        return internal_error_response(exc)

@app.route("/api/dashboard/top-products", methods=["GET", "OPTIONS"])
@token_required
def api_top_products():
    bid = get_current_business_id()
    try:
        rows = execute_read_query_params("SELECT product_name, stock_quantity, selling_price, cost_price FROM products WHERE business_id = %s ORDER BY stock_quantity DESC LIMIT 10", (bid,))
        margin_amount = [float((r["selling_price"] or 0) - (r["cost_price"] or 0)) for r in rows]
        margin_pct = [
            round(((r["selling_price"] or 0) - (r["cost_price"] or 0)) / (r["selling_price"] or 1) * 100, 1)
            if r["selling_price"]
            else 0
            for r in rows
        ]
        return jsonify({
            "labels": [r["product_name"] for r in rows],
            "stock": [int(r["stock_quantity"] or 0) for r in rows],
            "margin": margin_pct,
            "margin_amount": margin_amount,
            "margin_pct": margin_pct
        })
    except Exception as exc:
        return internal_error_response(exc)

@app.route("/api/dashboard/employee-stats", methods=["GET", "OPTIONS"])
@token_required
def api_employee_stats():
    bid = get_current_business_id()
    try:
        rows = execute_read_query_params("SELECT status, COUNT(*) AS cnt, COALESCE(AVG(salary),0) AS avg_salary FROM employees WHERE business_id = %s GROUP BY status", (bid,))
        return jsonify({
            "labels": [r["status"] for r in rows],
            "counts": [int(r["cnt"]) for r in rows],
            "avg_salary": [round(float(r["avg_salary"]), 2) for r in rows]
        })
    except Exception as exc:
        return internal_error_response(exc)

@app.route("/metrics")
def metrics():
    return Response(generate_latest(REGISTRY), mimetype=CONTENT_TYPE_LATEST)

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

# Start Server
register_swagger_docs(app)
_init_chat_db()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
