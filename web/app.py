"""
Intelligent Business Agent – Web Dashboard & Chatbot
Flask application running on port 5001.
"""

import os
import uuid
import time
import sqlite3
import json
import requests
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Optional

import jwt
import psycopg2
import psycopg2.extras
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for,
    g,
    Response,
    stream_with_context,
)
from dotenv import load_dotenv
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    REGISTRY,
)

load_dotenv()

# ── configuration ────────────────────────────────────────────────────
AGENT_API_URL = os.getenv("AGENT_API_URL", "http://127.0.0.1:5000")
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://admin:root@localhost:5432/test_db"
)
CHAT_DB_PATH = os.getenv("CHAT_DB_PATH", "chat_history.db")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super-secret-key-change-me")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET", "super-secret-business-key-2026")

# Allowed origins for CORS
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001,http://localhost:5173").split(",")


@dataclass(frozen=True)
class AuthError(Exception):
    message: str
    status_code: int = 401


def _extract_bearer_token(auth_header: Optional[str]) -> str:
    if not auth_header:
        raise AuthError("Authorization header is required")

    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise AuthError("Authorization header must use Bearer token")

    return token.strip()


def _decode_jwt_identity(auth_header: Optional[str], secret_key: str) -> dict[str, Any]:
    token = _extract_bearer_token(auth_header)

    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("Invalid authentication token") from exc

    user_id = payload.get("user_id")
    business_id = payload.get("business_id")
    if not user_id or not business_id:
        raise AuthError("Token is missing required identity claims")

    return {"user_id": str(user_id), "business_id": str(business_id)}


def token_required(route_handler):
    @wraps(route_handler)
    def decorated(*args, **kwargs):
        try:
            identity = _decode_jwt_identity(
                request.headers.get("Authorization"),
                app.config["JWT_SECRET_KEY"],
            )
        except AuthError as exc:
            return jsonify({"message": exc.message}), exc.status_code

        g.user_id = identity["user_id"]
        g.business_id = identity["business_id"]
        return route_handler(*args, **kwargs)

    return decorated


def get_current_business_id():
    return getattr(g, "business_id", None)


# ═══════════════════════════════════════════════════════════════════
# Prometheus metrics
# ═══════════════════════════════════════════════════════════════════
REQUEST_COUNT = Counter(
    "web_http_requests_total",
    "Total HTTP requests to the web dashboard",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "web_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120],
)
CHAT_MESSAGES_TOTAL = Counter(
    "web_chat_messages_total",
    "Total chat messages sent",
    ["role"],
)
CHAT_AGENT_LATENCY = Histogram(
    "web_chat_agent_response_seconds",
    "Time the backend agent takes to respond",
    buckets=[0.5, 1, 2, 5, 10, 30, 60, 120],
)
ACTIVE_CONVERSATIONS = Gauge(
    "web_active_conversations",
    "Number of active chat conversations",
)
DASHBOARD_API_ERRORS = Counter(
    "web_dashboard_api_errors_total",
    "Total errors from dashboard data API",
    ["endpoint"],
)

SAFE_INTERNAL_ERROR_MESSAGE = "An internal server error occurred. Please try again later."


def _internal_error_response(exc: Exception | None = None, *, field: str = "error"):
    if exc is not None:
        app.logger.error("Unhandled API exception: %s", exc, exc_info=True)
    return jsonify({field: SAFE_INTERNAL_ERROR_MESSAGE}), 500


@app.before_request
def _start_timer():
    g.start_time = time.time()


@app.after_request
def _record_metrics(response):
    # CORS headers
    origin = request.headers.get("Origin", "")
    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
        response.headers["Access-Control-Allow-Credentials"] = "true"

    # Metrics
    if request.path == "/metrics":
        return response
    
    latency = time.time() - getattr(g, "start_time", time.time())
    endpoint = request.endpoint or "unknown"
    REQUEST_COUNT.labels(request.method, endpoint, response.status_code).inc()
    REQUEST_LATENCY.labels(request.method, endpoint).observe(latency)
    return response


@app.route("/metrics")
def metrics():
    return Response(generate_latest(REGISTRY), mimetype=CONTENT_TYPE_LATEST)


# ═══════════════════════════════════════════════════════════════════
# SQLite helpers – chat history
# ═══════════════════════════════════════════════════════════════════
def _get_chat_db():
    if "chat_db" not in g:
        g.chat_db = sqlite3.connect(CHAT_DB_PATH)
        g.chat_db.row_factory = sqlite3.Row
    return g.chat_db


@app.teardown_appcontext
def _close_chat_db(exc):
    db = g.pop("chat_db", None)
    if db is not None:
        db.close()


def _init_chat_db():
    """Initialize chat database with tables if they don't exist."""
    db = sqlite3.connect(CHAT_DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            conversation_id TEXT PRIMARY KEY,
            title           TEXT NOT NULL DEFAULT 'New Chat',
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role        TEXT NOT NULL CHECK(role IN ('user','assistant')),
            content     TEXT NOT NULL,
            intent      TEXT DEFAULT NULL,
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
        );
        """
    )
    
    # Check if intent column exists (for backward compatibility)
    try:
        db.execute("SELECT intent FROM messages LIMIT 1")
    except sqlite3.OperationalError:
        db.execute("ALTER TABLE messages ADD COLUMN intent TEXT DEFAULT NULL")
        db.commit()
    
    db.close()


# ═══════════════════════════════════════════════════════════════════
# PostgreSQL helpers – dashboard data
# ═══════════════════════════════════════════════════════════════════
def _pg_conn():
    return psycopg2.connect(DATABASE_URL)


def _pg_query(sql, params=None):
    conn = _pg_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params or ())
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        return rows
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════
# Page routes
# ═══════════════════════════════════════════════════════════════════
@app.route("/")
def index():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", active_page="dashboard")


@app.route("/chatbot")
@app.route("/chatbot/<conv_id>")
def chatbot(conv_id=None):
    return render_template("chatbot.html", active_page="chatbot", conv_id=conv_id)


# ═══════════════════════════════════════════════════════════════════
# Dashboard API endpoints (last 24 h data)
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/dashboard/summary")
@token_required
def api_dashboard_summary():
    cutoff = (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%d")
    business_id = get_current_business_id()
    try:
        txn = _pg_query(
            """
            SELECT
                COALESCE(SUM(CASE WHEN type='Revenue' THEN amount END), 0) AS total_revenue,
                COALESCE(SUM(CASE WHEN type='Expense' THEN amount END), 0) AS total_expenses,
                COUNT(*) AS total_transactions
            FROM daily_transactions
            WHERE business_id = %s
              AND transaction_date >= %s
            """,
            (business_id, cutoff),
        )
        alerts = _pg_query(
            """
            SELECT COUNT(*) AS active_alerts
            FROM alerts
            WHERE business_id = %s
              AND status = 'Active'
              AND created_at >= %s
            """,
            (business_id, cutoff),
        )
        row = txn[0] if txn else {}
        alert_row = alerts[0] if alerts else {}
        return jsonify(
            {
                "total_revenue": float(row.get("total_revenue", 0)),
                "total_expenses": float(row.get("total_expenses", 0)),
                "net_profit": float(row.get("total_revenue", 0))
                - float(row.get("total_expenses", 0)),
                "total_transactions": int(row.get("total_transactions", 0)),
                "active_alerts": int(alert_row.get("active_alerts", 0)),
            }
        )
    except Exception as e:
        return _internal_error_response(e)


@app.route("/api/dashboard/revenue-vs-expense")
@token_required
def api_revenue_vs_expense():
    cutoff = (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%d")
    business_id = get_current_business_id()
    try:
        rows = _pg_query(
            """
            SELECT category, type,
                   COALESCE(SUM(amount), 0) AS total
            FROM daily_transactions
            WHERE transaction_date >= %s AND business_id = %s
            GROUP BY category, type
            ORDER BY total DESC
            """,
            (cutoff, business_id),
        )
        revenue_cats = {}
        expense_cats = {}
        for r in rows:
            cat = r["category"] or "Other"
            amt = float(r["total"])
            if r["type"] == "Revenue":
                revenue_cats[cat] = revenue_cats.get(cat, 0) + amt
            else:
                expense_cats[cat] = expense_cats.get(cat, 0) + amt

        all_cats = sorted(set(list(revenue_cats.keys()) + list(expense_cats.keys())))
        return jsonify(
            {
                "labels": all_cats,
                "revenue": [revenue_cats.get(c, 0) for c in all_cats],
                "expenses": [expense_cats.get(c, 0) for c in all_cats],
            }
        )
    except Exception as e:
        return _internal_error_response(e)


@app.route("/api/dashboard/transactions-by-category")
@token_required
def api_transactions_by_category():
    cutoff = (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%d")
    business_id = get_current_business_id()
    try:
        rows = _pg_query(
            """
            SELECT category, COUNT(*) as cnt
            FROM daily_transactions
            WHERE transaction_date >= %s AND business_id = %s
            GROUP BY category
            ORDER BY cnt DESC
            """,
            (cutoff, business_id),
        )
        return jsonify(
            {
                "labels": [r["category"] or "Other" for r in rows],
                "data": [int(r["cnt"]) for r in rows],
            }
        )
    except Exception as e:
        return _internal_error_response(e)


@app.route("/api/dashboard/sales-trend")
@token_required
def api_sales_trend():
    cutoff = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    business_id = get_current_business_id()
    try:
        rows = _pg_query(
            """
            SELECT transaction_date,
                   COALESCE(SUM(CASE WHEN type='Revenue' THEN amount END), 0) AS revenue,
                   COALESCE(SUM(CASE WHEN type='Expense' THEN amount END), 0) AS expenses
            FROM daily_transactions
            WHERE transaction_date >= %s AND business_id = %s
            GROUP BY transaction_date
            ORDER BY transaction_date
            """,
            (cutoff, business_id),
        )
        return jsonify(
            {
                "labels": [r["transaction_date"].isoformat() for r in rows],
                "revenue": [float(r["revenue"]) for r in rows],
                "expenses": [float(r["expenses"]) for r in rows],
            }
        )
    except Exception as e:
        return _internal_error_response(e)


@app.route("/api/dashboard/alerts-by-severity")
@token_required
def api_alerts_by_severity():
    business_id = get_current_business_id()
    try:
        rows = _pg_query(
            """
            SELECT severity, COUNT(*) AS cnt
            FROM alerts
            WHERE status = 'Active' AND business_id = %s
            GROUP BY severity
            """,
            (business_id,)
        )
        return jsonify(
            {
                "labels": [r["severity"] for r in rows],
                "data": [int(r["cnt"]) for r in rows],
            }
        )
    except Exception as e:
        return _internal_error_response(e)


@app.route("/api/dashboard/health-scores")
@token_required
def api_health_scores():
    business_id = get_current_business_id()
    try:
        rows = _pg_query(
            """
            SELECT bhs.overall_score, bhs.cash_score,
                   bhs.profitability_score, bhs.growth_score,
                   bhs.cost_control_score, bhs.risk_score,
                   b.business_name
            FROM business_health_scores bhs
            JOIN businesses b ON b.business_id = bhs.business_id
            WHERE bhs.business_id = %s
            ORDER BY bhs.calculated_at DESC
            LIMIT 5
            """,
            (business_id,)
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
    except Exception as e:
        return _internal_error_response(e)


@app.route("/api/dashboard/top-products")
@token_required
def api_top_products():
    business_id = get_current_business_id()
    try:
        rows = _pg_query(
            """
            SELECT p.product_name, p.stock_quantity, p.selling_price, p.cost_price
            FROM products p
            WHERE p.business_id = %s
            ORDER BY p.stock_quantity DESC
            LIMIT 10
            """,
            (business_id,)
        )
        return jsonify(
            {
                "labels": [r["product_name"] for r in rows],
                "stock": [int(r["stock_quantity"] or 0) for r in rows],
                "margin": [
                    float((r["selling_price"] or 0) - (r["cost_price"] or 0))
                    for r in rows
                ],
            }
        )
    except Exception as e:
        return _internal_error_response(e)


@app.route("/api/dashboard/financial-overview")
@token_required
def api_financial_overview():
    business_id = get_current_business_id()
    try:
        rows = _pg_query(
            """
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
            """,
            (business_id,)
        )
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
    except Exception as e:
        return _internal_error_response(e)


@app.route("/api/dashboard/employee-stats")
@token_required
def api_employee_stats():
    business_id = get_current_business_id()
    try:
        rows = _pg_query(
            """
            SELECT status, COUNT(*) AS cnt, COALESCE(AVG(salary),0) AS avg_salary
            FROM employees
            WHERE business_id = %s
            GROUP BY status
            """,
            (business_id,)
        )
        return jsonify(
            {
                "labels": [r["status"] for r in rows],
                "counts": [int(r["cnt"]) for r in rows],
                "avg_salary": [round(float(r["avg_salary"]), 2) for r in rows],
            }
        )
    except Exception as e:
        return _internal_error_response(e)


@app.route("/api/dashboard/recent-transactions")
@token_required
def api_recent_transactions():
    limit = request.args.get("limit", 20, type=int)
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    business_id = get_current_business_id()
    try:
        base_sql = """
            SELECT transaction_id, transaction_date, type, category,
                   amount, description
            FROM daily_transactions
            WHERE business_id = %s
        """
        params = [business_id]
        if search:
            base_sql += " AND (description ILIKE %s OR category ILIKE %s)"
            params.extend([f"%{search}%", f"%{search}%"])
        if category:
            base_sql += " AND category = %s"
            params.append(category)
        base_sql += " ORDER BY transaction_date DESC, transaction_id DESC LIMIT %s"
        params.append(limit)
        rows = _pg_query(base_sql, tuple(params))
        for r in rows:
            r["amount"] = float(r["amount"] or 0)
            if r.get("transaction_date"):
                r["transaction_date"] = r["transaction_date"].isoformat()
        return jsonify({"transactions": rows})
    except Exception as e:
        return _internal_error_response(e)


@app.route("/api/dashboard/sales-target")
@token_required
def api_sales_target():
    business_id = get_current_business_id()
    try:
        rows = _pg_query(
            """
            SELECT b.business_name, b.monthly_target_revenue,
                   COALESCE(SUM(CASE WHEN dt.type='Revenue' THEN dt.amount END), 0) AS current_revenue
            FROM businesses b
            LEFT JOIN daily_transactions dt ON dt.business_id = b.business_id
                AND EXTRACT(MONTH FROM dt.transaction_date) = EXTRACT(MONTH FROM CURRENT_DATE)
                AND EXTRACT(YEAR FROM dt.transaction_date) = EXTRACT(YEAR FROM CURRENT_DATE)
            WHERE b.business_id = %s
            GROUP BY b.business_id, b.business_name, b.monthly_target_revenue
            ORDER BY current_revenue DESC
            LIMIT 1
            """,
            (business_id,)
        )
        if rows:
            row = rows[0]
            target = float(row["monthly_target_revenue"] or 100000)
            current = float(row["current_revenue"] or 0)
            pct = round((current / target * 100), 1) if target > 0 else 0
            return jsonify({
                "business_name": row["business_name"],
                "current_revenue": current,
                "target_revenue": target,
                "percentage": pct,
            })
        return jsonify({"current_revenue": 0, "target_revenue": 100000, "percentage": 0})
    except Exception as e:
        return _internal_error_response(e)


@app.route("/api/dashboard/categories")
@token_required
def api_categories():
    business_id = get_current_business_id()
    try:
        rows = _pg_query(
            "SELECT DISTINCT category FROM daily_transactions WHERE business_id = %s ORDER BY category",
            (business_id,)
        )
        return jsonify({"categories": [r["category"] for r in rows if r["category"]]})
    except Exception as e:
        return _internal_error_response(e)


# ═══════════════════════════════════════════════════════════════════
# Chatbot API endpoints
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/chat/conversations", methods=["GET"])
@token_required
def api_list_conversations():
    db = _get_chat_db()
    rows = db.execute(
        "SELECT * FROM conversations ORDER BY updated_at DESC"
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/chat/conversations", methods=["POST"])
@token_required
def api_create_conversation():
    """Create a new conversation."""
    if request.is_json:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Invalid or missing JSON payload"}), 400
    else:
        data = {}
    
    conv_id = str(uuid.uuid4())
    title = data.get("title", "New Chat") if data else "New Chat"
    db = _get_chat_db()
    db.execute(
        "INSERT INTO conversations (conversation_id, title) VALUES (?, ?)",
        (conv_id, title),
    )
    db.commit()
    
    ACTIVE_CONVERSATIONS.inc()
    return jsonify({"conversation_id": conv_id, "title": title}), 201


@app.route("/api/chat/conversations/<conv_id>", methods=["DELETE"])
@token_required
def api_delete_conversation(conv_id):
    db = _get_chat_db()
    db.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
    db.execute("DELETE FROM conversations WHERE conversation_id = ?", (conv_id,))
    db.commit()
    
    ACTIVE_CONVERSATIONS.dec()
    return jsonify({"status": "deleted"}), 200


@app.route("/api/chat/conversations/<conv_id>/messages", methods=["GET"])
@token_required
def api_get_messages(conv_id):
    db = _get_chat_db()
    rows = db.execute(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at",
        (conv_id,),
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/chat/send", methods=["POST"])
@token_required
def api_chat_send():
    """
    Send a message to the agent and store the exchange.
    Expects JSON: { conversation_id, message }
    """
    data = request.get_json(force=True, silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid or missing JSON payload"}), 400
    
    conv_id = data.get("conversation_id")
    user_msg = data.get("message", "").strip()

    if not conv_id or not user_msg:
        return jsonify({"error": "conversation_id and message are required"}), 400

    db = _get_chat_db()

    # Check if conversation exists, if not create it
    exists = db.execute(
        "SELECT 1 FROM conversations WHERE conversation_id = ?", (conv_id,)
    ).fetchone()
    if not exists:
        db.execute(
            "INSERT INTO conversations (conversation_id, title) VALUES (?, ?)",
            (conv_id, user_msg[:50]),
        )
        ACTIVE_CONVERSATIONS.inc()

    # Store user message
    db.execute(
        "INSERT INTO messages (conversation_id, role, content) VALUES (?, 'user', ?)",
        (conv_id, user_msg),
    )
    db.commit()

    # Update conversation title if it's still "New Chat"
    conv_row = db.execute(
        "SELECT title FROM conversations WHERE conversation_id = ?", (conv_id,)
    ).fetchone()
    if conv_row and conv_row["title"] == "New Chat":
        db.execute(
            "UPDATE conversations SET title = ?, updated_at = datetime('now') WHERE conversation_id = ?",
            (user_msg[:60], conv_id),
        )
        db.commit()

    CHAT_MESSAGES_TOTAL.labels("user").inc()

    def generate_stream():
        agent_start = time.time()
        full_assistant_msg = ""
        intent_value = None
        clarification_data = None

        try:
            # Call the agent API with streaming
            resp = requests.get(
                f"{AGENT_API_URL}/api/v1/query",
                params={"input-query": user_msg, "thread-id": conv_id},
                timeout=120,
                stream=True,
            )
            
            for line in resp.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if decoded.startswith("data: "):
                        yield decoded + "\n\n"
                        payload = decoded[6:]
                        try:
                            chunk_data = json.loads(payload)
                            t = chunk_data.get("type")
                            if t == "token":
                                full_assistant_msg += chunk_data.get("content", "")
                            elif t == "final":
                                intent_value = chunk_data.get("intent_str")
                            elif t == "clarification":
                                clarification_data = chunk_data.get("clarification")
                                intent_value = chunk_data.get("intent_str")
                            elif t == "error":
                                full_assistant_msg = "⚠️ Error: " + chunk_data.get("error", "Unknown")
                                intent_value = chunk_data.get("intent_str")
                        except json.JSONDecodeError:
                            pass

            CHAT_AGENT_LATENCY.observe(time.time() - agent_start)
            
        except requests.exceptions.RequestException as exc:
            err_msg = f"Could not reach agent: {exc}"
            yield f"data: {json.dumps({'type': 'error', 'error': err_msg})}\n\n"
            full_assistant_msg = f"⚠️ Error: {err_msg}"
        except Exception as exc:
            err_msg = f"Unexpected error: {exc}"
            yield f"data: {json.dumps({'type': 'error', 'error': err_msg})}\n\n"
            full_assistant_msg = f"⚠️ Error: {err_msg}"

        CHAT_MESSAGES_TOTAL.labels("assistant").inc()

        # Determine final response text
        if clarification_data:
            if isinstance(clarification_data, str):
                final_text = clarification_data
            else:
                final_text = clarification_data.get("message", "Could you please clarify your question?")
        else:
            final_text = full_assistant_msg

        # Store assistant response in database
        db2 = sqlite3.connect(CHAT_DB_PATH)
        db2.execute(
            "INSERT INTO messages (conversation_id, role, content, intent) VALUES (?, 'assistant', ?, ?)",
            (conv_id, final_text, intent_value),
        )
        db2.execute(
            "UPDATE conversations SET updated_at = datetime('now') WHERE conversation_id = ?",
            (conv_id,),
        )
        db2.commit()
        db2.close()

    response = Response(stream_with_context(generate_stream()), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache, no-transform'
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Connection'] = 'keep-alive'
    return response


# ═══════════════════════════════════════════════════════════════════
# Bootstrap
# ═══════════════════════════════════════════════════════════════════
_init_chat_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)