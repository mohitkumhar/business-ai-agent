import os

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

from logger.logger import logger

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:root@localhost:5432/test_db",
)


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


_FORBIDDEN = [
    "insert ",
    "update ",
    "delete ",
    "drop ",
    "alter ",
    "truncate ",
    "create ",
]


def _assert_read_only_select(sql: str) -> str:
    """Normalize SQL and ensure a single read-only SELECT (or WITH ... SELECT)."""
    s = sql.strip().rstrip(";")
    cleaned = s.lower()
    if not (cleaned.startswith("select") or cleaned.startswith("with")):
        raise ValueError("Only SELECT or WITH...SELECT queries are allowed for safety.")
    if s.count(";") > 0:
        raise ValueError("Multiple SQL statements are not allowed.")
    for keyword in _FORBIDDEN:
        if keyword in cleaned:
            raise ValueError(f"Forbidden SQL keyword detected: {keyword.strip()}")
    return s


def explain_validate_select(sql: str) -> None:
    """
    Run EXPLAIN on the query without returning rows. Catches invalid aliases,
    missing columns, and bad JOINs that validators often miss.
    """
    s = _assert_read_only_select(sql)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        try:
            cur.execute("EXPLAIN (COSTS OFF) " + s)
        finally:
            cur.close()
    finally:
        conn.close()



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


def execute_read_query_params(sql: str, params: tuple | list | None = None) -> list[dict]:
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
