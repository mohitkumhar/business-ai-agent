"""
Intelligent Business Agent – Web Dashboard & Chatbot
Flask application running on port 5001.
Provides:
  • Dashboard with last-24-hour company charts
  • Chatbot UI that proxies queries to the backend agent API
  • Persistent chat-history storage (SQLite)
"""

import os
import time
import sqlite3
import sqlparse
from sqlparse.sql import Where  # <-- Moved here with other imports
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
    redirect,
    url_for,
    g,
    Response,
)
from dotenv import load_dotenv
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
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
# Tenant scoping validation
# ═══════════════════════════════════════════════════════════════════
def validate_tenant_scoping(query: str, business_id: str) -> bool:
    """
    Validate that a SQL query includes proper business_id scoping in WHERE clause.
    Uses sqlparse to parse the query structure.
    """
    if not query or not business_id:
        return False

    parsed = sqlparse.parse(query)
    if not parsed:
        return False

    stmt = parsed[0]
    # Ensure it's a SELECT statement
    if stmt.get_type() != "SELECT":
        return True  # Non-SELECT queries handled separately

    # Check for WHERE clause
    where_clause = next(
        (token for token in stmt.tokens if isinstance(token, Where)), None
    )
    if not where_clause:
        return False

    # Check if business_id is in the where clause
    query_str = where_clause.value.lower()
    return "business_id" in query_str and business_id.lower() in query_str


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


@app.before_request
def _start_timer():
    g.start_time = time.time()


@app.after_request
def _record_metrics(response):
    # CORS headers for Next.js dashboard
    origin = request.headers.get("Origin", "")
    if origin in (
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
    ):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
        response.headers["Access-Control-Allow-Credentials"] = "true"

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
    """Return a per-request SQLite connection (stored on flask.g)."""
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
    """Create chat tables if they don't exist, and migrate if needed."""
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
    # migrate: add intent column if it was missing (older DB)
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
    """Execute a read-only query and return list[dict] with tenant validation."""
    # Validate tenant scoping before execution
    business_id = get_current_business_id()
    if business_id and not validate_tenant_scoping(sql, business_id):
        app.logger.warning(f"Tenant scoping violation detected in query: {sql[:200]}")
        raise ValueError("Security Violation: Query missing proper business_id scoping")

    conn = _pg_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params or ())
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        return rows
    finally:
        conn.close()


SAFE_INTERNAL_ERROR_MESSAGE = (
    "An internal server error occurred. Please try again later."
)


def _internal_error_response(exc: Exception | None = None, *, field: str = "error"):
    if exc is not None:
        app.logger.error("Unhandled API exception: %s", exc, exc_info=True)
    return jsonify({field: SAFE_INTERNAL_ERROR_MESSAGE}), 500


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
# Dashboard API endpoints (all with tenant scoping via _pg_query)
# ═══════════════════════════════════════════════════════════════════


@app.route("/api/dashboard/summary")
@token_required
def api_dashboard_summary():
    """KPI summary cards – totals for last 24 h."""
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


# The rest of your dashboard endpoints would go here...
# (api_revenue_vs_expense, api_transactions_by_category, etc.)


# ═══════════════════════════════════════════════════════════════════
# Bootstrap
# ═══════════════════════════════════════════════════════════════════
_init_chat_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
