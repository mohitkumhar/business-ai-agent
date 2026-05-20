import re
from datetime import date

from db_config import get_db_connection, get_db_schema
from intents.database_request_graph.advisory_nodes import _resolve_business_id
from intents.database_request_graph.structures import (
    BusinessInsightOutput,
    DateRangeOutput,
    EntityExtractionOutput,
    SQLGenerationOutput,
    SQLValidationOutput,
)
from intents.database_request_graph.subgraph import DatabaseRequestGraphState
from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt
from llm.base_llm import base_llm
from logger.logger import logger

AVAILABLE_TABLES: list[str] = [
    "alerts",
    "business_health_scores",
    "businesses",
    "daily_transactions",
    "decision_outcomes",
    "decisions",
    "employees",
    "financial_records",
    "products",
    "roles",
    "users",
]

TABLE_DESCRIPTIONS: dict[str, str] = {
    "alerts": "Business alerts with severity (Low/Medium/High) and status (Active/Resolved)",
    "business_health_scores": "Overall business health metrics - cash, profitability, growth, cost-control, risk scores",
    "businesses": "Business registration — name, industry, owner, monthly_target_revenue, risk_appetite (table name is businesses, plural)",

    "daily_transactions": "Daily revenue & expense transactions with categories and amounts",
    "decision_outcomes": "Outcomes of past decisions with actual profit impact",
    "decisions": "Business decisions (Marketing/Hiring/Pricing/Expansion) with risk levels and success probability",
    "employees": "Employee records - name, role, salary, status (Active/Left)",
    "financial_records": "Monthly financial summaries — total_revenue, total_expenses, net_profit, cash_balance, loans_due (month/year)",
    "products": "Product catalog - cost price, selling price, stock quantity",
    "roles": "Roles defined for each business",
    "users": "System users with email, password hash, and role",
}


# Defining LLM
# =================================
date_range_llm = base_llm.with_structured_output(DateRangeOutput)
entity_llm = base_llm.with_structured_output(EntityExtractionOutput)
sql_gen_llm = base_llm.with_structured_output(SQLGenerationOutput)
sql_val_llm = base_llm.with_structured_output(SQLValidationOutput)
insight_llm = base_llm.with_structured_output(BusinessInsightOutput)



# NODE 1 - resolve_data_range
# =================================

# def resolve_data_range(state):
def resolve_data_range(state: DatabaseRequestGraphState):
    """Extract / infer the date-range the user is asking about."""

    user_query = state["user_query"]
    today_str = date.today().isoformat()

    logger.info(f"Resolving date range for user query: '{user_query}'")

    prompt = f"""You are a date-range extraction assistant.
Today's date is {today_str}.

Extract the date range from the following user query.
If no specific dates are mentioned, infer a reasonable range from context
("this month", "last quarter", "recent", etc.).
If absolutely no time reference exists, return null for both dates (= all time).

Common mappings:
  "this month"   → 1st of current month … today
  "last month"   → 1st … last day of previous month
  "this year"    → Jan 1 of current year … today
  "last quarter" → appropriate quarter boundaries
  "last 7 days"  → 7 days ago … today
  "yesterday"    → yesterday … yesterday
  "today"        → today … today

User Query: {user_query}"""

    try:
        logger.info("Invoking date_range_llm to resolve date range...")
        result = date_range_llm.invoke(prompt)
        logger.info(f"Date range resolved: {result}")
        return {
            "date_range_start": result.start_date or "",
            "date_range_end": result.end_date or "",
            "date_range_description": result.description,
        }
    except Exception as exc:
        logger.error("resolve_data_range failed: %s", exc, exc_info=True)
        return {
            "date_range_start": "",
            "date_range_end": "",
            "date_range_description": "All available data (no date range detected)",
        }



#  NODE 2 - validate_entities  (human-in-the-loop)
# =================================

def validate_entities(state: DatabaseRequestGraphState):
    """Extract table/column entities.  Uses interrupt() when ambiguous."""

    user_query = state["user_query"]

    table_info = "\n".join(
        f"  • {t}: {TABLE_DESCRIPTIONS[t]}" for t in AVAILABLE_TABLES
    )
    logger.info(f"Validating entities for user query: '{user_query}'")
    prompt = f"""You are an entity extraction assistant for a PostgreSQL business database.

Available tables:
{table_info}

From the user query, determine:
1. Which table(s) are needed to answer this query
2. Which specific columns are referenced — use **exact** PostgreSQL column names from the schema (e.g. total_revenue not \"revenue\")
3. Your confidence level (high / medium / low)
4. Which tables are ambiguous - i.e. you are unsure whether the user means them

Concept → table mapping hints:
  sales / revenue as daily line-items   → daily_transactions (columns: amount, type, transaction_date; type values 'Revenue' / 'Expense')
  monthly revenue, P&L, "how much revenue last month" → financial_records (columns: total_revenue, total_expenses, net_profit, month, year — NOT "revenue"/"expense" alone)
  expenses / costs (daily)   → daily_transactions
  profit / financial summary (monthly) → financial_records
  staff / payroll            → employees
  health score               → business_health_scores
  company / business profile / targets → businesses
  product / inventory        → products
  decision / strategy        → decisions, decision_outcomes
  alert / warning            → alerts
  user / login               → users
  role / permission          → roles

ONLY include tables from the available list above.
If the query clearly maps to one or two tables, set confidence = "high".
If the mapping is uncertain, list the candidates in ambiguous_tables and set confidence = "low".

User Query: {user_query}"""

    try:
        logger.info("Invoking entity_llm to validate entities...")
        result = entity_llm.invoke(prompt)
        logger.info(f"Entity extraction result: {result}")
    except Exception as exc:
        logger.error("validate_entities LLM call failed: %s", exc, exc_info=True)
        # safe fallback - let later stages deal with it
        return {
            "target_tables": ["daily_transactions"],
            "target_columns": [],
            "entities_valid": True,
        }

    valid_tables = [t for t in result.tables if t in AVAILABLE_TABLES]
    ambiguous   = [t for t in result.ambiguous_tables if t in AVAILABLE_TABLES]

    # CASE 1: no matching tables at all - ask user to clarify which category they mean
    if not valid_tables and not ambiguous:
        logger.warning("No matching or ambiguous tables found for query. Interrupting for clarification.")
        clarification = interrupt({
            "type": "clarification_needed",
            "reason": "no_matching_tables",
            "message": (
                "I couldn't determine which data you're asking about. "
                "Could you please clarify?\n\n"
                "Available data categories:\n"
                "  • Financial records & transactions\n"
                "  • Products & inventory\n"
                "  • Employees & staffing\n"
                "  • Business decisions & outcomes\n"
                "  • Alerts & health scores\n\n"
                "Please rephrase your question or pick a category."
            ),
            "options": AVAILABLE_TABLES,
        })
        # After resume - clarification holds the user's chosen value
        logger.info(f"User clarification received: {clarification}")
        chosen = _resolve_clarification(clarification)
        logger.info(f"Resolved clarification to tables: {chosen}")
        return {
            "target_tables": chosen,
            "target_columns": result.columns if result.columns else [],
            "entities_valid": True,
        }

    # CASE 2: ambiguous / low confidence
    if ambiguous and result.confidence == "low":
        logger.info(f"Entity extraction is ambiguous. Valid tables: {valid_tables}, Ambiguous tables: {ambiguous}")
        options_str = ", ".join(ambiguous)
        clarification = interrupt({
            "type": "clarification_needed",
            "reason": "ambiguous_tables",
            "message": (
                f"Your question could relate to multiple data sources: "
                f"{options_str}.\nWhich one did you mean?"
            ),
            "options": ambiguous,
        })
        logger.info(f"User clarification received for ambiguous tables: {clarification}")
        chosen = _resolve_clarification(clarification)
        logger.info(f"Resolved clarification for ambiguous tables to: {chosen}")
        return {
            "target_tables": chosen,
            "target_columns": result.columns if result.columns else [],
            "entities_valid": True,
        }

    # CASE 3: confident extraction
    tables = valid_tables if valid_tables else ambiguous[:1]
    logger.info(f"Entity extraction confident. Using tables: {tables}")
    return {
        "target_tables": tables,
        "target_columns": result.columns if result.columns else [],
        "entities_valid": len(tables) > 0,
    }


def _resolve_clarification(clarification) -> list[str]:
    """Turn whatever the user replied with into a list of valid table names."""
    logger.info(f"Resolving user clarification: {clarification}")
    if isinstance(clarification, str):
        # Could be a table name or a keyword
        matched = [
            t for t in AVAILABLE_TABLES
            if t == clarification.strip().lower()
            or clarification.strip().lower() in t
        ]
        logger.info(f"Matched clarification to tables: {matched}")
        return matched if matched else ["daily_transactions"]
    if isinstance(clarification, list):
        matched = [t for t in clarification if t in AVAILABLE_TABLES]
        logger.info(f"Matched clarification list to tables: {matched}")
        return matched if matched else ["daily_transactions"]
    logger.warning(f"Unhandled clarification type: {type(clarification)}. Defaulting to daily_transactions.")
    return ["daily_transactions"]


#  NODE 3 - fetch_table_schema
# =================================

def fetch_table_schema(state: DatabaseRequestGraphState):
    """Pull the real column / constraint info for the target tables."""
    logger.info(f"Fetching table schema for state: {state}")
    target_tables = state.get("target_tables", [])
    logger.info(f"Target tables for schema fetch: {target_tables}")
    if not target_tables:
        logger.warning("No target tables specified for schema fetch. Falling back to full schema.")
        # fallback to full schema
        return {"table_schema": get_db_schema()}

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        schema_parts: list[str] = []
        related_tables_seen: set[str] = set(target_tables)

        for table in target_tables:
            # columns
            cur.execute(
                """
                SELECT column_name, data_type, is_nullable, column_default
                FROM   information_schema.columns
                WHERE  table_schema = 'public' AND table_name = %s
                ORDER  BY ordinal_position;
                """,
                (table,),
            )
            columns = cur.fetchall()

            if columns:
                schema_parts.append(f"\nTable: {table}")
                schema_parts.append("-" * 50)
                for col_name, dtype, nullable, default in columns:
                    null_str = "NULL" if nullable == "YES" else "NOT NULL"
                    def_str = f" DEFAULT {default}" if default else ""
                    schema_parts.append(
                        f"  {col_name} ({dtype}, {null_str}{def_str})"
                    )

                # check constraints (useful for enum-like columns)
                cur.execute(
                    """
                    SELECT conname, pg_get_constraintdef(c.oid)
                    FROM   pg_constraint c
                    JOIN   pg_class t ON c.conrelid = t.oid
                    JOIN   pg_namespace n ON t.relnamespace = n.oid
                    WHERE  t.relname = %s AND n.nspname = 'public'
                           AND c.contype = 'c';
                    """,
                    (table,),
                )
                checks = cur.fetchall()
                if checks:
                    schema_parts.append("  CHECK constraints:")
                    for con_name, con_def in checks:
                        schema_parts.append(f"    {con_name}: {con_def}")
            else:
                schema_parts.append(f"\nTable '{table}' - not found in database.")

        # related tables via FK (one level deep)
        for table in list(target_tables):
            cur.execute(
                """
                SELECT DISTINCT ccu.table_name
                FROM   information_schema.table_constraints  tc
                JOIN   information_schema.constraint_column_usage ccu
                       ON ccu.constraint_name = tc.constraint_name
                       AND ccu.table_schema   = tc.table_schema
                WHERE  tc.table_name = %s
                       AND tc.constraint_type = 'FOREIGN KEY'
                       AND tc.table_schema = 'public';
                """,
                (table,),
            )
            for (ref_table,) in cur.fetchall():
                if ref_table in related_tables_seen:
                    continue
                related_tables_seen.add(ref_table)

                cur.execute(
                    """
                    SELECT column_name, data_type, is_nullable
                    FROM   information_schema.columns
                    WHERE  table_schema = 'public' AND table_name = %s
                    ORDER  BY ordinal_position;
                    """,
                    (ref_table,),
                )
                ref_cols = cur.fetchall()
                if ref_cols:
                    schema_parts.append(
                        f"\nRelated table (FK): {ref_table}"
                    )
                    schema_parts.append("-" * 50)
                    for col_name, dtype, nullable in ref_cols:
                        null_str = "NULL" if nullable == "YES" else "NOT NULL"
                        schema_parts.append(
                            f"  {col_name} ({dtype}, {null_str})"
                        )

        cur.close()
        conn.close()
        return {"table_schema": "\n".join(schema_parts)}

    except Exception as exc:
        logger.error("fetch_table_schema failed: %s", exc, exc_info=True)
        return {"table_schema": get_db_schema()}




def _chain_prior_block_for_sql(state: DatabaseRequestGraphState) -> str:
    """Build optional context block; kept out of f-string braces to avoid backslash restrictions."""
    prior = (state.get("chain_prior_summaries") or "").strip()
    if not prior:
        return ""
    header = (
        "CONTEXT FROM EARLIER STEPS IN THIS REQUEST "
        "(use to narrow tables/filters; still validate against schema):"
    )
    return header + "\n" + prior + "\n"


#  NODE 4 - SQL_generation
# =================================

def sql_generation(state: DatabaseRequestGraphState):
    """Ask the LLM to produce a SELECT query."""
    from logger.agent_debug import log_node_enter, log_node_exit

    t0 = log_node_enter(
        "SQL_generation",
        {**state, "intent": "database_request"},
        "Searching your business data — drafting SQL…",
    )

    user_query            = state["user_query"]
    table_schema          = state.get("table_schema", "")
    date_start            = state.get("date_range_start", "")
    date_end              = state.get("date_range_end", "")
    date_desc             = state.get("date_range_description", "")
    target_tables         = state.get("target_tables", [])
    prev_sql              = state.get("generated_sql", "")
    prev_error            = state.get("sql_validation_error", "")

    # retry context
    retry_block = ""
    if prev_error and prev_sql:
        retry_block = f"""
IMPORTANT - your previous attempt had errors.  Fix them.
Previous SQL : {prev_sql}
Error        : {prev_error}
"""

    date_filter = ""
    if date_start and date_end:
        date_filter = (
            f"- Apply date filter: BETWEEN '{date_start}' AND '{date_end}' "
            f"on the appropriate date column (transaction_date, created_at, calculated_at …)"
        )
    elif date_start:
        date_filter = f"- Apply date filter: >= '{date_start}'"
    elif date_end:
        date_filter = f"- Apply date filter: <= '{date_end}'"

    business_id = _resolve_business_id(state)
    # BUG4 FIX: warn loudly when business_id is missing so data-leak is visible in logs
    if not business_id:
        logger.warning("[WARN] business_id is empty - query will return all businesses data (potential data leak)")
    financial_rules = ""
    _fin_q = re.search(
        r"\b(revenue|sales|profit|expense|cash|loans?|financial|p&l|monthly|margin)\b",
        user_query,
        re.IGNORECASE,
    )
    if business_id and (
        "financial_records" in target_tables
        or ("financial_records" in table_schema and _fin_q)
    ):
        financial_rules = f"""
MANDATORY — financial_records + businesses scoping (prevent cross-tenant leaks):
- Alias **financial_records AS fr** and **businesses AS b** (PostgreSQL table name is `businesses`).
- JOIN: `INNER JOIN businesses b ON fr.business_id = b.business_id`
- Always add: `AND b.business_id = '{business_id}'::uuid`
- Allowed financial columns only: fr.total_revenue, fr.total_expenses, fr.net_profit, fr.cash_balance, fr.loans_due, fr.month, fr.year, fr.business_id — never `revenue` / `expenses` as bare names.
"""

    prompt = f"""You are a PostgreSQL expert.  Generate **one** SQL SELECT query.

DATABASE SCHEMA
{table_schema}

TARGET TABLES : {', '.join(target_tables)}
DATE RANGE    : {date_desc}
OPERATING BUSINESS_ID (filter all financial queries) : {business_id or '(resolve from businesses table if absent)'}

RULES
- ONLY SELECT statements.  No INSERT / UPDATE / DELETE / DROP / ALTER / TRUNCATE / CREATE.
- Use **only** table and column names that appear verbatim in DATABASE SCHEMA (no invented columns like \"revenue\" if the schema has total_revenue).
- If you alias a table (e.g. financial_records AS fr), every qualified column must use that alias — never reference another alias (e.g. tr.\\*) unless that alias is in FROM/JOIN.
{financial_rules}
- Use proper JOIN multitable queries when the schema requires it; for financial summaries always join `businesses b` as above when filtering financial_records.
- Add meaningful column aliases.
- ORDER BY where it improves readability.
- LIMIT 100 unless the user explicitly asks for more.
- Use COALESCE for NULLs in aggregated / displayed columns.
- Use SUM / AVG / COUNT and GROUP BY when totals or averages are requested.
- For financial_records time filters without a date column, filter by month and year integers (see schema), not transaction_date.
{date_filter}

BUG4 MANDATORY FILTER — business_id scoping for daily_transactions:
- When querying daily_transactions (alias dt), always add: `AND dt.business_id = '{business_id}'::uuid`
- When querying financial_records (alias fr), always add: `AND fr.business_id = '{business_id}'::uuid`
- If business_id is empty string above, omit this filter (already warned in logs).

DOMAIN HINTS
- net_profit   = total_revenue - total_expenses  (financial_records)
- financial_records has total_revenue, total_expenses — there is NO column named revenue or expenses on this table
- daily_transactions.type ∈ ('Revenue', 'Expense')
- employees.status ∈ ('Active', 'Left')
- decisions.decision_type ∈ ('Marketing', 'Hiring', 'Pricing', 'Expansion')
- decisions.status ∈ ('Approved', 'Rejected', 'Modified')
- alerts.severity ∈ ('Low', 'Medium', 'High')
- alerts.status ∈ ('Active', 'Resolved')
{retry_block}

USER QUESTION
{user_query}

{_chain_prior_block_for_sql(state)}

Return the SQL query and a short plain-English explanation."""

    try:
        logger.info("[SQL GEN] tables=%s | retry=%s", target_tables, state.get("sql_retry_count", 0))
        logger.info("Invoking sql_gen_llm to generate SQL query.")
        result = sql_gen_llm.invoke(prompt)
        logger.info("[SQL GEN] query_preview=%s", (result.sql_query or "")[:200])
        out = {
            "generated_sql": result.sql_query,
            "sql_explanation": result.explanation,
        }
        log_node_exit(
            "SQL_generation",
            {**state, **out, "route": "sql_generated"},
            t0,
        )
        return out
    except Exception as exc:
        logger.error("sql_generation failed: %s", exc, exc_info=True)
        log_node_exit(
            "SQL_generation",
            {**state, "route": "sql_gen_error"},
            t0,
        )
        return {
            "generated_sql": "",
            "sql_explanation": f"SQL generation failed: {exc}",
        }



#  NODE 5 - SQL_validation
# =================================

FORBIDDEN_KEYWORDS = [
    "insert ", "update ", "delete ", "drop ", "alter ",
    "truncate ", "create ", "grant ", "revoke ",
]

def sql_validation(state: DatabaseRequestGraphState):
    """Validate generated SQL (safety + LLM-based correctness)."""

    generated_sql  = state.get("generated_sql", "")
    table_schema   = state.get("table_schema", "")
    retry_count    = state.get("sql_retry_count", 0)

    def _fail(reason: str):
        new_count = retry_count + 1
        logger.warning(f"SQL validation failed (attempt {new_count}/3): {reason}")
        return {
            "is_sql_valid": False,
            "sql_validation_error": reason,
            "sql_retry_count": new_count,
            "route": "sql_invalid" if new_count < 3 else "sql_failed",
        }

    # guard: no SQL at all
    if not generated_sql.strip():
        return _fail("No SQL query was generated.")

    cleaned = generated_sql.strip().lower()

    # must be SELECT or WITH (CTE)
    if not (cleaned.startswith("select") or cleaned.startswith("with")):
        return _fail("Query must start with SELECT (or WITH for CTEs).")

    # forbidden keywords
    for kw in FORBIDDEN_KEYWORDS:
        if kw in cleaned:
            return _fail(f"Forbidden keyword detected: {kw.strip()}")

    # Deterministic check: planner catches bad aliases / missing columns LLM often misses
    try:
        from db_config import explain_validate_select

        explain_validate_select(generated_sql)
    except ValueError as exc:
        return _fail(str(exc))
    except Exception as exc:
        msg = str(exc).strip().split("\n")[0]
        logger.info("[SQL VALID] planner=fail | retry=%s | err=%s", retry_count, msg[:200])
        return _fail(msg or "SQL failed database validation (EXPLAIN).")

    logger.info(
        "[SQL VALID] planner=ok | retry=%s | sql_preview=%s",
        retry_count,
        (generated_sql or "")[:120].replace("\n", " "),
    )

    # LLM-based deeper validation
    prompt = f"""You are a SQL validation expert.  Validate the query below.

VALIDATION RULES — READ CAREFULLY BEFORE FLAGGING ERRORS:
- BETWEEN 'date' AND 'date' with IDENTICAL dates is VALID PostgreSQL.
  It means "filter for that exact day". Do NOT flag this as an error.
- CURRENT_DATE - INTERVAL '1 day' is valid PostgreSQL syntax.
- COALESCE(SUM(col), 0) is valid and preferred for nullable aggregations.
- Only flag GENUINE SQL errors: wrong table names, wrong column names,
  missing required clauses, or real syntax errors.  Do NOT invent issues.

SQL:
{generated_sql}

Schema:
{table_schema}

Check:
1. Valid PostgreSQL syntax
2. All referenced tables/columns exist in the schema — qualified names must use an alias that appears in FROM/JOIN (e.g. if only \"fr\" is defined, reject tr.*)
3. financial_records uses total_revenue / total_expenses, not revenue / expenses as column names
4. Correct JOIN conditions
5. Aggregate functions paired with GROUP BY
6. No dangerous operations
7. Logical sense for a business database

If issues are fixable, provide corrected_sql.  Otherwise set is_valid=false."""

    try:
        logger.info("Performing LLM-based SQL validation.")
        result = sql_val_llm.invoke(prompt)

        if result.is_valid:
            logger.info("SQL validation successful.")
            logger.info("[SQL VALID] llm=is_valid | corrected=0")
            return {
                "is_sql_valid": True,
                "sql_validation_error": "",
                "route": "sql_valid",
            }

        # LLM found issues but offered a fix
        if result.corrected_sql and result.corrected_sql.strip():
            logger.info(f"SQL validation found issues and provided a correction. Original: '{generated_sql}', Corrected: '{result.corrected_sql}'")
            return {
                "generated_sql": result.corrected_sql,
                "is_sql_valid": True,
                "sql_validation_error": "",
                "route": "sql_valid",
            }

        return _fail("; ".join(result.issues) if result.issues else "Unknown validation error")

    except Exception as exc:
        # LLM unavailable - trust basic checks that already passed
        logger.warning("LLM SQL validation failed (%s); accepting basic checks", exc, exc_info=True)
        return {
            "is_sql_valid": True,
            "sql_validation_error": "",
            "route": "sql_valid",
        }



#  NODE 6 - execute_query
# =================================

def execute_query(state: DatabaseRequestGraphState):
    """Run the validated SQL against Postgres."""
    import time as _time

    generated_sql = state.get("generated_sql", "")
    is_valid      = state.get("is_sql_valid", False)

    if not is_valid or not generated_sql.strip():
        error_msg = state.get(
            "sql_validation_error",
            "SQL query is invalid or missing.",
        )
        logger.error(f"Cannot execute query: {error_msg}")
        return {
            "query_results": "[]",
            "execution_error": error_msg,
            "has_results": False,
        }

    clean_sql = generated_sql.strip().rstrip(";")
    logger.info(f"Executing SQL query: {clean_sql}")

    try:
        import json

        from db_config import execute_read_query

        _t0 = _time.perf_counter()
        rows = execute_read_query(clean_sql)
        _ms = int((_time.perf_counter() - _t0) * 1000)
        logger.info("[SQL EXEC] rows_returned=%s | duration_ms=%s", len(rows), _ms)
        logger.info(f"Query executed successfully. Found {len(rows)} rows.")
        return {
            "query_results": json.dumps(rows, default=str, indent=2),
            "execution_error": "",
            "has_results": len(rows) > 0,
        }
    except ValueError as exc:
        logger.error(f"SQL safety check failed: {exc}", exc_info=True)
        return {
            "query_results": "[]",
            "execution_error": f"Safety check: {exc}",
            "has_results": False,
        }
    except RuntimeError as exc:
        logger.error(f"SQL execution error: {exc}", exc_info=True)
        return {
            "query_results": "[]",
            "execution_error": f"Execution error: {exc}",
            "has_results": False,
        }
    except Exception as exc:
        logger.critical(f"Unexpected error during query execution: {exc}", exc_info=True)
        return {
            "query_results": "[]",
            "execution_error": f"Unexpected error: {exc}",
            "has_results": False,
        }



#  NODE 7 - logging
# =================================

import json
from datetime import datetime


def logging_node(state: DatabaseRequestGraphState):
    """Persist an audit-log entry for the query lifecycle."""

    log_data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "user_query": state.get("user_query", ""),
        "date_range": {
            "start": state.get("date_range_start", ""),
            "end": state.get("date_range_end", ""),
            "description": state.get("date_range_description", ""),
        },
        "target_tables": state.get("target_tables", []),
        "generated_sql": state.get("generated_sql", ""),
        "sql_valid": state.get("is_sql_valid", False),
        "has_results": state.get("has_results", False),
        "execution_error": state.get("execution_error", ""),
    }

    logger.info("DB-QUERY-LOG  %s", json.dumps(log_data, default=str))

    return {"log_entry": json.dumps(log_data, default=str)}



#  NODE 8 - post_query_operations
# =================================

def post_query_operations(state: DatabaseRequestGraphState):
    """Enrich raw query results with basic statistics."""
    logger.info("Starting post-query operations.")

    query_results   = state.get("query_results", "[]")
    execution_error = state.get("execution_error", "")
    has_results     = state.get("has_results", False)

    if execution_error:
        logger.warning(f"Skipping post-query operations due to execution error: {execution_error}")
        return {
            "processed_data": json.dumps({
                "status": "error",
                "error": execution_error,
                "suggestion": "Please try rephrasing your question or check if the data exists.",
            })
        }

    if not has_results:
        logger.info("No results found, creating 'no_data' response.")
        return {
            "processed_data": json.dumps({
                "status": "no_data",
                "message": "No records found matching your query.",
                "suggestion": "Try broadening the date range or adjusting your criteria.",
            })
        }

    try:
        rows = json.loads(query_results)
        logger.info(f"Successfully loaded {len(rows)} rows from query results for processing.")
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Failed to decode query_results JSON: {e}", exc_info=True)
        rows = []

    processed: dict = {
        "status": "success",
        "total_records": len(rows),
        "data": rows,
        "metadata": {
            "tables_queried": state.get("target_tables", []),
            "date_range": state.get("date_range_description", ""),
            "sql_explanation": state.get("sql_explanation", ""),
        },
    }

    # numeric column summaries
    if rows:
        numeric_summaries: dict = {}
        for key in rows[0]:
            values: list[float] = []
            for row in rows:
                val = row.get(key)
                if isinstance(val, (int, float)):
                    values.append(float(val))
                elif isinstance(val, str):
                    try:
                        values.append(float(val))
                    except (ValueError, TypeError):
                        pass
            if values:
                numeric_summaries[key] = {
                    "min": round(min(values), 2),
                    "max": round(max(values), 2),
                    "avg": round(sum(values) / len(values), 2),
                    "sum": round(sum(values), 2),
                    "count": len(values),
                }
        if numeric_summaries:
            processed["numeric_summaries"] = numeric_summaries
            logger.info(f"Generated numeric summaries for columns: {list(numeric_summaries.keys())}")

    logger.info("Post-query operations completed successfully.")
    return {"processed_data": json.dumps(processed, default=str)}



#  NODE 9 - business_insight_generator
# =================================

def business_insight_generator(state: DatabaseRequestGraphState):
    """Use the LLM to derive actionable insights from the data."""

    processed_data  = state.get("processed_data", "{}")
    user_query      = state.get("user_query", "")
    execution_error = state.get("execution_error", "")

    if execution_error:
        logger.warning(f"Skipping insight generation due to execution error: {execution_error}")
        return {
            "business_insight": json.dumps({
                "summary": "Unable to generate insights because the data query failed.",
                "error": execution_error,
                "key_metrics": [],
                "trends": [],
                "recommendations": ["Please rephrase your question and try again."],
                "risk_flags": [],
            })
        }

    prior = (state.get("chain_prior_summaries") or "").strip()
    prior_block = f"\nEarlier analysis steps in this request already established:\n{prior}\nBuild on this; avoid contradicting concrete numbers from above unless the database data clearly supersedes them.\n" if prior else ""

    prompt = f"""You are a senior business-intelligence analyst.

A small-business owner asked: "{user_query}"
{prior_block}
Here is the data retrieved from their database:
{processed_data}

Provide:
1. **Summary** - a clear executive summary of the findings
2. **Key Metrics** - the most important numbers / figures
3. **Trends** - any notable patterns
4. **Recommendations** - practical, actionable advice for a small-business owner
5. **Risk Flags** - any warning signs or concerns

Rules:
- Be specific with numbers and percentages.
- Compare values where possible ("revenue is 20 % higher than expenses").
- If data is limited, acknowledge it and suggest what extra data would help.
- Use ₹ or $ for monetary values as appropriate.
- Flag concerning trends clearly.
"""

    try:
        logger.info("Invoking insight_llm to generate business insights.")
        result = insight_llm.invoke(prompt)
        logger.info("Business insights generated successfully.")
        return {
            "business_insight": json.dumps({
                "summary": result.summary,
                "key_metrics": result.key_metrics,
                "trends": result.trends,
                "recommendations": result.recommendations,
                "risk_flags": result.risk_flags,
            }, default=str)
        }
    except Exception as exc:
        logger.error("business_insight_generator failed: %s", exc, exc_info=True)
        return {
            "business_insight": json.dumps({
                "summary": "Data retrieved successfully but automatic insight generation is currently unavailable.",
                "key_metrics": [],
                "trends": [],
                "recommendations": ["Review the raw data manually for insights."],
                "risk_flags": [],
            })
        }


#  NODE 10 - format_response_of_business_insight_generator
# =================================

def format_response_of_business_insight_generator(state: DatabaseRequestGraphState, config: RunnableConfig):
    """Produce a polished, user-friendly markdown response."""

    business_insight = state.get("business_insight", "{}")
    processed_data   = state.get("processed_data", "{}")
    user_query       = state.get("user_query", "")
    execution_error  = state.get("execution_error", "")

    # fast path for errors
    if execution_error:
        logger.info(f"Formatting an error response due to execution error: {execution_error}")
        formatted = (
            "I ran into a problem while fetching your data:\n\n"
            f"**Issue**: {execution_error}\n\n"
            "**What you can do**:\n"
            "- Rephrase the question\n"
            "- Make sure you are asking about existing data categories\n"
            "- Check that the date range is reasonable"
        )
        return {
            "formatted_response": formatted,
            "messages": [{"role": "assistant", "content": formatted}],
        }

    # parse payloads
    try:
        insight = json.loads(business_insight)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Could not parse business_insight JSON: {e}. Using raw string.", exc_info=True)
        insight = {"summary": business_insight}

    try:
        data = json.loads(processed_data)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Could not parse processed_data JSON: {e}. Using empty dict.", exc_info=True)
        data = {}

    total_records = data.get("total_records", 0)
    status        = data.get("status", "N/A")

    # If there's no data, skip the heavy table formatting and just return the summary/message
    if status == "no_data" or str(total_records) == "0":
        msg = insight.get("summary", data.get("message", "No records found matching your query."))
        formatted_msg = f"{msg}\n\n*Suggestion: {data.get('suggestion', 'Try modifying your search query.')}*"
        return {
            "formatted_response": formatted_msg,
            "messages": [{"role": "assistant", "content": formatted_msg}],
        }

    prompt = f"""You are a professional business assistant.  Format the following
analysis into a clear, polished response for a small-business owner.

ORIGINAL QUESTION : {user_query}

BUSINESS INSIGHTS :
{json.dumps(insight, indent=2, default=str)}

DATA SUMMARY :
- Total records : {total_records}
- Status        : {status}

FORMATTING RULES
1. Answer the user's question directly, first.
2. Use bullet points and **bold** for emphasis.
3. Show monetary values with proper symbols (₹ / $) and thousand separators.
4. List actionable recommendations.
5. Mention risk flags / warnings if any.
6. If there is tabular data, show the top rows clearly.
7. Do NOT expose SQL, table names, or any technical internals.
8. Keep the tone professional yet friendly.

Respond ONLY with the formatted answer - no preamble, no meta-commentary."""

    try:
        logger.info("Invoking base_llm to format the final response.")
        response = base_llm.invoke(prompt, config=config)
        formatted = response.content
        logger.info("Final response formatted successfully by LLM.")
    except Exception as exc:
        logger.error("format_response LLM call failed: %s", exc, exc_info=True)

        # graceful fallback
        logger.info("Falling back to manual response formatting.")
        parts = [f"**Summary**: {insight.get('summary', 'Data retrieved.')}"]
        for label, key in [
            ("Key Metrics", "key_metrics"),
            ("Recommendations", "recommendations"),
            ("Risk Flags", "risk_flags"),
        ]:
            items = insight.get(key, [])
            if items:
                parts.append(f"\n**{label}**:")
                for item in items:
                    parts.append(f"  • {item}")
        formatted = "\n".join(parts)

    return {
        "formatted_response": formatted,
        "messages": [{"role": "assistant", "content": formatted}],
    }
