import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:root@localhost:5432/test_db",
)

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

_FORBIDDEN = ["insert ", "update ", "delete ", "drop ", "alter ", "truncate ", "create "]
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
        cur.execute(s, params or ())
        results = cur.fetchall()
        cur.close()
        return [dict(row) for row in results]
    except Exception as e:
        raise RuntimeError(f"SQL execution error: {str(e)}")
    finally:
        conn.close()

# Note: get_db_schema() is omitted from this minimal fix to reduce PR bloat.
# If you need it, ensure it is protected by @token_required in app.py.

