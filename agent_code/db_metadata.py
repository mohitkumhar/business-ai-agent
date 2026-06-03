from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


metadata = sa.MetaData()


businesses = sa.Table(
    "businesses",
    metadata,
    sa.Column(
        "business_id",
        postgresql.UUID(as_uuid=True),
        server_default=sa.text("gen_random_uuid()"),
        primary_key=True,
    ),
    sa.Column("business_name", sa.String(150), nullable=False),
    sa.Column("industry_type", sa.String(100)),
    sa.Column("owner_name", sa.String(150)),
    sa.Column("monthly_target_revenue", sa.Numeric(14, 2)),
    sa.Column("risk_appetite", sa.String(20)),
    sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    sa.Column(
        "city",
        sa.String(100),
        comment="City/location of the business collected at onboarding",
    ),
    sa.Column(
        "business_age",
        sa.String(50),
        comment="Owner-stated age of the business (e.g. 1-3 years)",
    ),
    sa.Column(
        "employees_range",
        sa.String(20),
        comment="Binned employee count from onboarding form",
    ),
    sa.Column(
        "biggest_challenge",
        sa.String(255),
        comment="Primary business challenges (can be multiple)",
    ),
    sa.Column(
        "finance_tracking_method",
        sa.String(50),
        comment="Current tools used for financial tracking",
    ),
    sa.Column(
        "onboarding_notes",
        sa.Text(),
        comment="Optional qualitative feedback provided during signup",
    ),
    sa.CheckConstraint(
        "monthly_target_revenue >= 0", name="businesses_monthly_target_revenue_check"
    ),
    sa.CheckConstraint(
        "risk_appetite IN ('Low', 'Medium', 'High')",
        name="businesses_risk_appetite_check",
    ),
    sa.CheckConstraint(
        "finance_tracking_method IN ('Excel/Sheets', 'App like Tally/Zoho', 'Notebook/Manual', 'Don''t track')",
        name="businesses_finance_tracking_method_check",
    ),
    sa.CheckConstraint(
        "employees_range IN ('Just me', '2–5', '6–15', '16–50', '51–100', '100+')",
        name="businesses_employees_range_check",
    ),
)

roles = sa.Table(
    "roles",
    metadata,
    sa.Column("role_id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
    sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("role_name", sa.String(100), nullable=False),
    sa.Column("description", sa.Text()),
    sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    sa.ForeignKeyConstraint(
        ["business_id"],
        ["businesses.business_id"],
        name="roles_business_id_fkey",
        ondelete="CASCADE",
    ),
    sa.UniqueConstraint(
        "business_id", "role_name", name="roles_business_id_role_name_key"
    ),
)

users = sa.Table(
    "users",
    metadata,
    sa.Column("user_id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
    sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("role_id", sa.BigInteger(), nullable=False),
    sa.Column("name", sa.String(150), nullable=False),
    sa.Column("email", sa.String(150), nullable=False, unique=True),
    sa.Column("password_hash", sa.Text(), nullable=False),
    sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    sa.Column(
        "phone",
        sa.String(20),
        comment="User contact number/WhatsApp collected during onboarding",
    ),
    sa.ForeignKeyConstraint(
        ["business_id"],
        ["businesses.business_id"],
        name="users_business_id_fkey",
        ondelete="CASCADE",
    ),
    sa.ForeignKeyConstraint(["role_id"], ["roles.role_id"], name="users_role_id_fkey"),
)

financial_records = sa.Table(
    "financial_records",
    metadata,
    sa.Column(
        "financial_record_id",
        sa.BigInteger(),
        sa.Identity(always=False),
        primary_key=True,
    ),
    sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("month", sa.Integer()),
    sa.Column("year", sa.Integer()),
    sa.Column("total_revenue", sa.Numeric(14, 2), server_default=sa.text("0")),
    sa.Column("total_expenses", sa.Numeric(14, 2), server_default=sa.text("0")),
    sa.Column("net_profit", sa.Numeric(14, 2)),
    sa.Column("cash_balance", sa.Numeric(14, 2)),
    sa.Column("loans_due", sa.Numeric(14, 2)),
    sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    sa.CheckConstraint(
        "month >= 1 AND month <= 12", name="financial_records_month_check"
    ),
    sa.CheckConstraint("year >= 2000", name="financial_records_year_check"),
    sa.ForeignKeyConstraint(
        ["business_id"],
        ["businesses.business_id"],
        name="financial_records_business_id_fkey",
        ondelete="CASCADE",
    ),
)

daily_transactions = sa.Table(
    "daily_transactions",
    metadata,
    sa.Column(
        "transaction_id", sa.BigInteger(), sa.Identity(always=False), primary_key=True
    ),
    sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("transaction_date", sa.Date(), nullable=False),
    sa.Column("type", sa.String(20)),
    sa.Column("category", sa.String(100)),
    sa.Column("amount", sa.Numeric(14, 2)),
    sa.Column("description", sa.Text()),
    sa.CheckConstraint("amount >= 0", name="daily_transactions_amount_check"),
    sa.CheckConstraint(
        "type IN ('Revenue', 'Expense')", name="daily_transactions_type_check"
    ),
    sa.ForeignKeyConstraint(
        ["business_id"],
        ["businesses.business_id"],
        name="daily_transactions_business_id_fkey",
        ondelete="CASCADE",
    ),
)

products = sa.Table(
    "products",
    metadata,
    sa.Column(
        "product_id", sa.BigInteger(), sa.Identity(always=False), primary_key=True
    ),
    sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("product_name", sa.String(150), nullable=False),
    sa.Column("cost_price", sa.Numeric(14, 2)),
    sa.Column("selling_price", sa.Numeric(14, 2)),
    sa.Column("stock_quantity", sa.Integer(), server_default=sa.text("0")),
    sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    sa.ForeignKeyConstraint(
        ["business_id"],
        ["businesses.business_id"],
        name="products_business_id_fkey",
        ondelete="CASCADE",
    ),
)

employees = sa.Table(
    "employees",
    metadata,
    sa.Column(
        "employee_id", sa.BigInteger(), sa.Identity(always=False), primary_key=True
    ),
    sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("name", sa.String(150)),
    sa.Column("role", sa.String(100)),
    sa.Column("salary", sa.Numeric(14, 2)),
    sa.Column("status", sa.String(20)),
    sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    sa.CheckConstraint("status IN ('Active', 'Left')", name="employees_status_check"),
    sa.ForeignKeyConstraint(
        ["business_id"],
        ["businesses.business_id"],
        name="employees_business_id_fkey",
        ondelete="CASCADE",
    ),
)

decisions = sa.Table(
    "decisions",
    metadata,
    sa.Column(
        "decision_id", sa.BigInteger(), sa.Identity(always=False), primary_key=True
    ),
    sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("decision_text", sa.Text()),
    sa.Column("decision_type", sa.String(50)),
    sa.Column("decision_score", sa.Numeric(5, 2)),
    sa.Column("risk_level", sa.String(20)),
    sa.Column("success_probability", sa.Numeric(5, 2)),
    sa.Column("status", sa.String(20)),
    sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    sa.CheckConstraint(
        "decision_type IN ('Marketing', 'Hiring', 'Pricing', 'Expansion')",
        name="decisions_decision_type_check",
    ),
    sa.CheckConstraint(
        "status IN ('Approved', 'Rejected', 'Modified')", name="decisions_status_check"
    ),
    sa.ForeignKeyConstraint(
        ["business_id"],
        ["businesses.business_id"],
        name="decisions_business_id_fkey",
        ondelete="CASCADE",
    ),
)

decision_outcomes = sa.Table(
    "decision_outcomes",
    metadata,
    sa.Column(
        "decision_outcome_id",
        sa.BigInteger(),
        sa.Identity(always=False),
        primary_key=True,
    ),
    sa.Column("decision_id", sa.BigInteger(), nullable=False),
    sa.Column("actual_result", sa.Text()),
    sa.Column("profit_impact", sa.Numeric(14, 2)),
    sa.Column("notes", sa.Text()),
    sa.Column("evaluated_at", sa.DateTime()),
    sa.ForeignKeyConstraint(
        ["decision_id"],
        ["decisions.decision_id"],
        name="decision_outcomes_decision_id_fkey",
        ondelete="CASCADE",
    ),
)

alerts = sa.Table(
    "alerts",
    metadata,
    sa.Column("alert_id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
    sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("alert_type", sa.String(100)),
    sa.Column("severity", sa.String(20)),
    sa.Column("message", sa.Text()),
    sa.Column("status", sa.String(20)),
    sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    sa.CheckConstraint(
        "severity IN ('Low', 'Medium', 'High')", name="alerts_severity_check"
    ),
    sa.CheckConstraint("status IN ('Active', 'Resolved')", name="alerts_status_check"),
    sa.ForeignKeyConstraint(
        ["business_id"],
        ["businesses.business_id"],
        name="alerts_business_id_fkey",
        ondelete="CASCADE",
    ),
)

business_health_scores = sa.Table(
    "business_health_scores",
    metadata,
    sa.Column(
        "health_score_id", sa.BigInteger(), sa.Identity(always=False), primary_key=True
    ),
    sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("overall_score", sa.Numeric(5, 2)),
    sa.Column("cash_score", sa.Numeric(5, 2)),
    sa.Column("profitability_score", sa.Numeric(5, 2)),
    sa.Column("growth_score", sa.Numeric(5, 2)),
    sa.Column("cost_control_score", sa.Numeric(5, 2)),
    sa.Column("risk_score", sa.Numeric(5, 2)),
    sa.Column(
        "calculated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")
    ),
    sa.ForeignKeyConstraint(
        ["business_id"],
        ["businesses.business_id"],
        name="business_health_scores_business_id_fkey",
        ondelete="CASCADE",
    ),
)
