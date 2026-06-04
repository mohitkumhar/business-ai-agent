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

# Tables that MUST be scoped by business_id to prevent data leakage
TENANT_TABLES = ["daily_transactions", "alerts", "products", "financial_records"]

def _assert_read_only_select(sql: str) -> str:
    """Normalize SQL and enforce read-only and tenant-scoping security rules."""
    s = sql.strip().rstrip(";")
    cleaned = s.lower()
    
    if not (cleaned.startswith("select") or cleaned.startswith("with")):
        raise ValueError("Only SELECT or WITH...SELECT queries are allowed.")
    if s.count(";") > 0:
        raise ValueError("Multiple SQL statements are not allowed.")
    
    # SQL Injection prevention
    for keyword in _FORBIDDEN:
        if keyword in cleaned:
            raise ValueError(f"Forbidden SQL keyword detected: {keyword.strip()}")
            
    # BOLA / Tenant Isolation Enforcement
    if any(table in cleaned for table in TENANT_TABLES):
        if "business_id" not in cleaned:
             raise ValueError("Security Violation: Tenant-scoped tables require a 'business_id' filter.")
             
    return s

def execute_read_query_params(sql: str, params: tuple | list | None = None) -> list[dict]:
    """
    Safely executes a SELECT query with tenant-scoping validation.
    Always use this function for any data fetched from the DB.
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