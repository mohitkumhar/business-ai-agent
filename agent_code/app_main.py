import json
import logging
import os
import re
import sys
import time
import traceback
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import openai
import pandas as pd
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from sqlalchemy import create_engine, text

from agent_code.api_errors import (
    AuthenticationError,
    DatabaseConnectionError,
    InvalidRequestError,
    RateLimitError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)
from agent_code.auth import require_api_key
from agent_code.auth_passwords import hash_password, verify_password
from agent_code.db_config import get_database_config
from agent_code.db_metadata import get_table_metadata
from agent_code.intents.database_request_graph.advanced_analytics import (
    run_advanced_analytics,
)
from agent_code.intents.database_request_graph.billing_analyzer import (
    BillingAnalyzer,
)
from agent_code.intents.database_request_graph.data_quality import run_data_quality
from agent_code.intents.database_request_graph.insight_generator import (
    InsightGenerator,
)
from agent_code.intents.database_request_graph.query_executor import QueryExecutor
from agent_code.intents.database_request_graph.report_generator import (
    ReportGenerator,
)
from agent_code.intents.database_request_graph.schema_analyzer import SchemaAnalyzer
from agent_code.intents.database_request_graph.sql_generator import SQLGenerator
from agent_code.intents.web_search.web_search import WebSearchAgent

load_dotenv()

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global state / configuration
# ---------------------------------------------------------------------------

DATABASE_CONFIG: Optional[Dict[str, Any]] = None
OPENAI_API_KEY: Optional[str] = None

# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


def initialize_app() -> None:
    """Load configuration and validate required environment variables."""
    global DATABASE_CONFIG, OPENAI_API_KEY

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set; AI features will be disabled.")

    db_config = get_database_config()
    if db_config:
        DATABASE_CONFIG = db_config
        logger.info("Database configuration loaded successfully.")
    else:
        logger.warning(
            "No database configuration found; database features will be unavailable."
        )


initialize_app()

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def get_engine() -> Any:
    """Create and return a SQLAlchemy engine from the global DATABASE_CONFIG."""
    if not DATABASE_CONFIG:
        raise DatabaseConnectionError("No database configuration available.")
    try:
        conn_str = (
            f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}"
            f"@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"
        )
        engine = create_engine(conn_str)
        return engine
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        raise DatabaseConnectionError(f"Failed to create database engine: {e}")


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------


@app.route("/health", methods=["GET"])
def health_check() -> Tuple[Dict[str, str], int]:
    """Return a simple health-check response."""
    return jsonify({"status": "healthy"}), 200


@app.route("/api/v1/query", methods=["POST"])
@require_api_key
def execute_query() -> Tuple[Dict[str, Any], int]:
    """
    Execute a natural-language query against the connected database.

    Request JSON body:
        - query (str): The natural language query.
        - top_k (int, optional): Number of top results to return. Default 10.

    Returns:
        JSON with keys:
            - success (bool)
            - data (list[dict] | None): Query results as list of dicts.
            - error (str | None): Error message if any.
            - sql (str | None): Generated SQL if applicable.
    """
    try:
        data = request.get_json()
        if not data or "query" not in data:
            raise InvalidRequestError("Missing 'query' in request body.")

        query_text = data["query"]
        top_k = data.get("top_k", 10)

        engine = get_engine()
        metadata = get_table_metadata(engine)
        schema_analyzer = SchemaAnalyzer(metadata)
        sql_gen = SQLGenerator(OPENAI_API_KEY, schema_analyzer)
        executor = QueryExecutor(engine)

        generated_sql = sql_gen.generate(query_text)
        if not generated_sql:
            return jsonify({"success": False, "error": "Failed to generate SQL."}), 400

        results = executor.execute(generated_sql, top_k=top_k)
        return jsonify({"success": True, "data": results, "sql": generated_sql}), 200

    except InvalidRequestError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except DatabaseConnectionError as e:
        return jsonify({"success": False, "error": str(e)}), 503
    except Exception as e:
        logger.error(f"Unexpected error in /api/v1/query: {e}")
        return jsonify({"success": False, "error": "Internal server error."}), 500


@app.route("/api/v1/insights", methods=["POST"])
@require_api_key
def generate_insights() -> Tuple[Dict[str, Any], int]:
    """
    Generate business insights from the database.

    Request JSON body:
        - focus_area (str, optional): Area to focus on (e.g., 'sales', 'inventory').
        - time_period (str, optional): Time period for analysis (e.g., 'last_30_days').

    Returns:
        JSON with keys:
            - success (bool)
            - insights (list[str] | None): List of insight statements.
            - error (str | None): Error message if any.
    """
    try:
        data = request.get_json() or {}
        focus_area = data.get("focus_area", "general")
        time_period = data.get("time_period", "last_30_days")

        engine = get_engine()
        metadata = get_table_metadata(engine)
        insight_gen = InsightGenerator(OPENAI_API_KEY, metadata)
        insights = insight_gen.generate(focus_area, time_period)

        return jsonify({"success": True, "insights": insights}), 200

    except DatabaseConnectionError as e:
        return jsonify({"success": False, "error": str(e)}), 503
    except Exception as e:
        logger.error(f"Unexpected error in /api/v1/insights: {e}")
        return jsonify({"success": False, "error": "Internal server error."}), 500


@app.route("/api/v1/report", methods=["POST"])
@require_api_key
def generate_report() -> Tuple[Dict[str, Any], int]:
    """
    Generate a structured business report.

    Request JSON body:
        - report_type (str): Type of report (e.g., 'sales_summary', 'inventory_status').
        - filters (dict, optional): Additional filters for the report.

    Returns:
        JSON with keys:
            - success (bool)
            - report (dict | None): The generated report data.
            - error (str | None): Error message if any.
    """
    try:
        data = request.get_json()
        if not data or "report_type" not in data:
            raise InvalidRequestError("Missing 'report_type' in request body.")

        report_type = data["report_type"]
        filters = data.get("filters", {})

        engine = get_engine()
        metadata = get_table_metadata(engine)
        report_gen = ReportGenerator(OPENAI_API_KEY, metadata)
        report = report_gen.generate(report_type, filters)

        return jsonify({"success": True, "report": report}), 200

    except InvalidRequestError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except DatabaseConnectionError as e:
        return jsonify({"success": False, "error": str(e)}), 503
    except Exception as e:
        logger.error(f"Unexpected error in /api/v1/report: {e}")
        return jsonify({"success": False, "error": "Internal server error."}), 500


@app.route("/api/v1/advanced-analytics", methods=["POST"])
@require_api_key
def advanced_analytics() -> Tuple[Dict[str, Any], int]:
    """
    Run advanced analytics (e.g., forecasting, clustering) on the data.

    Request JSON body:
        - analysis_type (str): Type of analysis (e.g., 'forecast', 'clustering').
        - parameters (dict, optional): Parameters for the analysis.

    Returns:
        JSON with keys:
            - success (bool)
            - results (dict | None): Analysis results.
            - error (str | None): Error message if any.
    """
    try:
        data = request.get_json()
        if not data or "analysis_type" not in data:
            raise InvalidRequestError("Missing 'analysis_type' in request body.")

        analysis_type = data["analysis_type"]
        parameters = data.get("parameters", {})

        engine = get_engine()
        results = run_advanced_analytics(engine, analysis_type, parameters)

        return jsonify({"success": True, "results": results}), 200

    except InvalidRequestError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except DatabaseConnectionError as e:
        return jsonify({"success": False, "error": str(e)}), 503
    except Exception as e:
        logger.error(f"Unexpected error in /api/v1/advanced-analytics: {e}")
        return jsonify({"success": False, "error": "Internal server error."}), 500


@app.route("/api/v1/data-quality", methods=["POST"])
@require_api_key
def data_quality() -> Tuple[Dict[str, Any], int]:
    """
    Run data quality checks on the database.

    Request JSON body:
        - checks (list[str], optional): Specific checks to run. If omitted, run all.

    Returns:
        JSON with keys:
            - success (bool)
            - results (dict | None): Data quality report.
            - error (str | None): Error message if any.
    """
    try:
        data = request.get_json() or {}
        checks = data.get("checks", None)

        engine = get_engine()
        results = run_data_quality(engine, checks)

        return jsonify({"success": True, "results": results}), 200

    except DatabaseConnectionError as e:
        return jsonify({"success": False, "error": str(e)}), 503
    except Exception as e:
        logger.error(f"Unexpected error in /api/v1/data-quality: {e}")
        return jsonify({"success": False, "error": "Internal server error."}), 500


@app.route("/api/v1/billing/analyze", methods=["POST"])
@require_api_key
def billing_analyze() -> Tuple[Dict[str, Any], int]:
    """
    Analyze billing data and return aggregated metrics.

    Request JSON body:
        - start_date (str, optional): Start date for analysis (ISO format). Default: 30 days ago.
        - end_date (str, optional): End date for analysis (ISO format). Default: today.
        - group_by (str, optional): Grouping dimension ('customer', 'product', 'region'). Default: 'customer'.
        - metrics (list[str], optional): Metrics to compute ('total_revenue', 'avg_order_value',
          'order_count', 'unique_customers'). Default: all metrics.

    Returns:
        JSON with keys:
            - success (bool)
            - data (list[dict] | None): List of aggregated billing records.
            - summary (dict | None): Overall summary statistics.
            - error (str | None): Error message if any.

    Raises:
        400 Bad Request: If required parameters are missing or invalid.
        503 Service Unavailable: If database connection fails.
    """
    try:
        data = request.get_json() or {}

        start_date = data.get("start_date", (datetime.utcnow() - timedelta(days=30)).isoformat())
        end_date = data.get("end_date", datetime.utcnow().isoformat())
        group_by = data.get("group_by", "customer")
        metrics = data.get("metrics", None)

        engine = get_engine()
        analyzer = BillingAnalyzer(engine)
        result = analyzer.analyze(
            start_date=start_date,
            end_date=end_date,
            group_by=group_by,
            metrics=metrics,
        )

        return jsonify({"success": True, "data": result["data"], "summary": result["summary"]}), 200

    except InvalidRequestError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except DatabaseConnectionError as e:
        return jsonify({"success": False, "error": str(e)}), 503
    except Exception as e:
        logger.error(f"Unexpected error in /api/v1/billing/analyze: {e}")
        return jsonify({"success": False, "error": "Internal server error."}), 500


@app.route("/api/v1/billing/analyze-all", methods=["POST"])
@require_api_key
def billing_analyze_all() -> Tuple[Dict[str, Any], int]:
    """
    Perform comprehensive billing analysis across all available dimensions and metrics.

    This endpoint runs a full billing analysis covering all grouping dimensions
    (customer, product, region) and all supported metrics. It is designed for
    generating complete billing overviews and dashboards.

    Request JSON body:
        - start_date (str, optional): Start date for analysis (ISO format). Default: 30 days ago.
        - end_date (str, optional): End date for analysis (ISO format). Default: today.
        - include_summary (bool, optional): Whether to include overall summary. Default: True.

    Returns:
        JSON with keys:
            - success (bool): Whether the analysis completed successfully.
            - data (dict | None): Nested dictionary with keys for each group_by dimension.
              Each dimension contains a list of aggregated records.
            - summary (dict | None): Overall summary statistics across all dimensions.
              Only present if include_summary is True.
            - error (str | None): Error message if the analysis failed.

    Raises:
        400 Bad Request: If date parameters are invalid.
        503 Service Unavailable: If the database connection fails.
        500 Internal Server Error: For unexpected failures during analysis.

    Example response:
        {
            "success": true,
            "data": {
                "customer": [...],
                "product": [...],
                "region": [...]
            },
            "summary": {
                "total_revenue": 123456.78,
                "total_orders": 500,
                "avg_order_value": 246.91
            }
        }
    """
    try:
        data = request.get_json() or {}

        start_date = data.get("start_date", (datetime.utcnow() - timedelta(days=30)).isoformat())
        end_date = data.get("end_date", datetime.utcnow().isoformat())
        include_summary = data.get("include_summary", True)

        engine = get_engine()
        analyzer = BillingAnalyzer(engine)

        dimensions = ["customer", "product", "region"]
        all_data = {}
        overall_summary = None

        for dim in dimensions:
            result = analyzer.analyze(
                start_date=start_date,
                end_date=end_date,
                group_by=dim,
                metrics=None,  # all metrics
            )
            all_data[dim] = result["data"]
            if include_summary and overall_summary is None:
                overall_summary = result["summary"]
            elif include_summary:
                # Merge summaries (simplified: take the first one as representative)
                pass

        return jsonify({"success": True, "data": all_data, "summary": overall_summary}), 200

    except InvalidRequestError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except DatabaseConnectionError as e:
        return jsonify({"success": False, "error": str(e)}), 503
    except Exception as e:
        logger.error(f"Unexpected error in /api/v1/billing/analyze-all: {e}")
        return jsonify({"success": False, "error": "Internal server error."}), 500


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------


@app.errorhandler(404)
def not_found(error: Any) -> Tuple[Dict[str, str], int]:
    return jsonify({"error": "Resource not found."}), 404


@app.errorhandler(405)
def method_not_allowed(error: Any) -> Tuple[Dict[str, str], int]:
    return jsonify({"error": "Method not allowed."}), 405


@app.errorhandler(500)
def internal_error(error: Any) -> Tuple[Dict[str, str], int]:
    return jsonify({"error": "Internal server error."}), 500


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
