import os
import re  # SECURITY FIX: Imported re for strict boundary matching
import sqlparse  # Added for SQL parsing

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

from logger.logger import logger

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:root@localhost:5432/test_db",
)

# SECURITY: First line of defense - simple string matching for dangerous keywords
_FORBIDDEN = [
    "DROP",
    "DELETE",
    "UPDATE",
    "INSERT",
    "ALTER",
    "TRUNCATE",
    "GRANT",
    "REVOKE",
    "EXECUTE",
]

# Tables that MUST be scoped by business_id to prevent data leakage
TENANT_TABLES = ["daily_transactions", "alerts", "products", "financial_records"]


def get_db_connection():
    """Returns a new psycopg2 connection to the PostgreSQL database."""
    return psycopg2.connect(DATABASE_URL)


def get_db_schema() -> str:
    """
    Reads all user tables and their columns from the database.
    Returns a formatted string the LLM can use to understand the schema.
    """
    query = """
        SELECT table_name, column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position;
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        schema_lines = []
        current_table = None
        for table_name, column_name, data_type, is_nullable in rows:
            if table_name != current_table:
                current_table = table_name
                schema_lines.append(f"\nTable: {table_name}")
                schema_lines.append("-" * 40)
            nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
            schema_lines.append(f"  {column_name} ({data_type}, {nullable})")

        return "\n".join(schema_lines)
    except Exception:
        logger.error("Error reading schema", exc_info=True)
        return "Error reading schema"


# SECURITY FIX: Second line of defense - strict regex boundary matching
_FORBIDDEN_PATTERN = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|execute)\b",
    re.IGNORECASE,
)


def _remove_string_literals(sql: str) -> str:
    """Replace string literal contents with empty strings for structural safety checks.
    Handles PostgreSQL's standard SQL escaping (doubled quotes).
    Backslash has no special meaning in standard_conforming_strings=on (the default)."""
    result = []
    in_single_quote = False
    in_double_quote = False

    for char in sql:
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            result.append(char)
        elif char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            result.append(char)
        elif not in_single_quote and not in_double_quote:
            result.append(char)

    return "".join(result)


def _has_business_id_filter(sql: str) -> bool:
    """
    Parse SQL to check if business_id filter exists in WHERE clause.
    Uses sqlparse to properly analyze query structure.
    """
    try:
        parsed = sqlparse.parse(sql)
        if not parsed:
            return False

        # Walk through the parsed tokens to find WHERE clause
        for statement in parsed:
            in_where = False
            for token in statement.tokens:
                if (
                    token.ttype is sqlparse.tokens.Keyword
                    and token.value.upper() == "WHERE"
                ):
                    in_where = True
                elif in_where and token.ttype is sqlparse.tokens.Keyword:
                    # Hit another keyword like GROUP BY, ORDER BY, etc.
                    in_where = False
                elif in_where and hasattr(token, "value"):
                    # Check for business_id in the WHERE clause
                    if "business_id" in token.value.lower():
                        return True
        return False
    except Exception as e:
        logger.warning(f"SQL parsing failed for tenant validation: {e}")
        # Fallback to simple string check
        where_pos = sql.lower().find("where")
        if where_pos != -1:
            after_where = sql[where_pos + 5 :].lower()
            # Look for business_id before next clause
            next_clause = min(
                after_where.find("group by"),
                after_where.find("order by"),
                after_where.find("limit"),
                after_where.find(";"),
            )
            if next_clause == -1:
                next_clause = len(after_where)
            where_clause = after_where[:next_clause]
            return "business_id" in where_clause
        return False


def _assert_read_only_select(sql: str) -> str:
    """Normalize SQL and ensure a single read-only SELECT (or WITH ... SELECT)."""
    s = sql.strip().rstrip(";")
    cleaned = s.lower()
    if not (cleaned.startswith("select") or cleaned.startswith("with")):
        raise ValueError("Only SELECT or WITH...SELECT queries are allowed for safety.")

    structural_sql = _remove_string_literals(s)
    structural_cleaned = structural_sql.lower()

    if structural_sql.count(";") > 0:
        raise ValueError("Multiple SQL statements are not allowed.")

    # SECURITY FIX: Execute regex search to catch newline/tab whitespace bypasses
    if _FORBIDDEN_PATTERN.search(cleaned):
        raise ValueError("Forbidden SQL keyword detected. Query blocked.")

    # Main branch keyword check - First line of defense
    for keyword in _FORBIDDEN:
        if keyword.lower() in structural_cleaned:
            raise ValueError(f"Forbidden SQL keyword detected: {keyword.strip()}")

    # Improved BOLA / Tenant Isolation Enforcement with SQL parsing
    if any(table in cleaned for table in TENANT_TABLES):
        if not _has_business_id_filter(s):
            raise ValueError(
                "Security Violation: Tenant-scoped tables require a 'business_id' filter in the WHERE clause."
            )

    return s


def explain_validate_select(sql: str) -> bool:
    """
    Validates SQL by running EXPLAIN against the database.
    If the DB raises an error, the SQL is invalid.

    Returns:
        True if the SQL is valid, False otherwise.
    """
    try:
        # First run the static analysis checks
        s = _assert_read_only_select(sql)

        # Actually execute the EXPLAIN query against the database
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute(f"EXPLAIN (COSTS OFF) {s}")
            cur.fetchall()  # Consume results to ensure no errors
            cur.close()
            logger.info(f"SQL validation successful for query: {s[:100]}...")
            return True
        except psycopg2.Error as e:
            logger.error(f"EXPLAIN validation failed: {e}")
            return False
        finally:
            conn.close()
    except ValueError as e:
        # Static validation failed
        logger.error(f"Static SQL validation failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during SQL validation: {e}", exc_info=True)
        return False


def execute_read_query(sql: str) -> list[dict]:
    """
    Safely executes a SELECT-only SQL query.
    Returns results as a list of dicts.
    """
    s = _assert_read_only_select(sql)

    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(s)
        results = cur.fetchall()
        cur.close()
        return [dict(row) for row in results]
    except Exception:
        logger.error("SQL execution error", exc_info=True)
        raise RuntimeError("SQL execution failed")
    finally:
        conn.close()


def execute_read_query_params(
    sql: str, params: tuple | list | None = None
) -> list[dict]:
    """
    Same safety rules as execute_read_query, but supports parameterized queries
    (psycopg2 %s placeholders). Use for all user-influenced predicates.
    """
    s = _assert_read_only_select(sql)
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cur.execute(s, params or ())
            results = cur.fetchall()
        finally:
            cur.close()
        return [dict(row) for row in results]
    except Exception:
        logger.error("SQL execution error", exc_info=True)
        raise RuntimeError("SQL execution failed")
    finally:
        conn.close()
