from flask import Blueprint, jsonify, request, Response, stream_with_context, g
from core_logic import *

dashboard_bp = Blueprint('dashboard_bp', __name__)

@dashboard_bp.route("/api/dashboard/summary", methods=["GET", "OPTIONS"])
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


@dashboard_bp.route("/api/dashboard/financial-overview", methods=["GET", "OPTIONS"])
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


@dashboard_bp.route("/api/dashboard/revenue-vs-expense", methods=["GET", "OPTIONS"])
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


@dashboard_bp.route("/api/dashboard/sales-trend", methods=["GET", "OPTIONS"])
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


@dashboard_bp.route("/api/dashboard/transactions-by-category", methods=["GET", "OPTIONS"])
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


@dashboard_bp.route("/api/dashboard/alerts-by-severity", methods=["GET", "OPTIONS"])
def api_alerts_by_severity():
    try:
        rows = execute_read_query_params(
            "SELECT severity, COUNT(*) AS cnt FROM alerts WHERE status='Active' GROUP BY severity"
        )
        return jsonify({"labels": [r["severity"] for r in rows], "data": [int(r["cnt"]) for r in rows]})
    except Exception as exc:
        return internal_error_response(exc)


@dashboard_bp.route("/api/dashboard/health-scores", methods=["GET", "OPTIONS"])
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


@dashboard_bp.route("/api/dashboard/top-products", methods=["GET", "OPTIONS"])
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


@dashboard_bp.route("/api/dashboard/employee-stats", methods=["GET", "OPTIONS"])
@token_required
def api_employee_stats():
    business_id = get_current_business_id()
    if not business_id:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        rows = execute_read_query_params(
            "SELECT status, COUNT(*) AS cnt, COALESCE(AVG(salary),0) AS avg_salary FROM employees WHERE business_id = %s GROUP BY status",
            (business_id,)
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


@dashboard_bp.route("/api/dashboard/recent-transactions", methods=["GET", "OPTIONS"])
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


@dashboard_bp.route("/api/dashboard/sales-target", methods=["GET", "OPTIONS"])
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


@dashboard_bp.route("/api/dashboard/categories", methods=["GET", "OPTIONS"])
def api_categories():
    try:
        rows = execute_read_query_params("SELECT DISTINCT category FROM daily_transactions ORDER BY category")
        return jsonify({"categories": [r["category"] for r in rows if r["category"]]})
    except Exception as exc:
        return internal_error_response(exc)


@dashboard_bp.route("/api/dashboard/business-info", methods=["GET", "OPTIONS"])
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
    _initialize_whatsapp_tables_safe()
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

@dashboard_bp.route("/api/dashboard/summary-sql", methods=["GET"])
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

@dashboard_bp.route("/api/dashboard/forecast", methods=["GET"])
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

