"""Create initial business schema.

Revision ID: 20260528_0001
Revises:
Create Date: 2026-05-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260528_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public")

    op.create_table(
        "businesses",
        sa.Column(
            "business_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("business_name", sa.String(length=150), nullable=False),
        sa.Column("industry_type", sa.String(length=100), nullable=True),
        sa.Column("owner_name", sa.String(length=150), nullable=True),
        sa.Column("monthly_target_revenue", sa.Numeric(14, 2), nullable=True),
        sa.Column("risk_appetite", sa.String(length=20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("business_age", sa.String(length=50), nullable=True),
        sa.Column("employees_range", sa.String(length=20), nullable=True),
        sa.Column("biggest_challenge", sa.String(length=255), nullable=True),
        sa.Column("finance_tracking_method", sa.String(length=50), nullable=True),
        sa.Column("onboarding_notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "monthly_target_revenue >= 0",
            name="businesses_monthly_target_revenue_check",
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
        sa.PrimaryKeyConstraint("business_id", name="businesses_pkey"),
        schema="public",
    )
    op.execute(
        "COMMENT ON COLUMN public.businesses.city IS 'City/location of the business collected at onboarding'"
    )
    op.execute(
        "COMMENT ON COLUMN public.businesses.business_age IS 'Owner-stated age of the business (e.g. 1-3 years)'"
    )
    op.execute(
        "COMMENT ON COLUMN public.businesses.employees_range IS 'Binned employee count from onboarding form'"
    )
    op.execute(
        "COMMENT ON COLUMN public.businesses.biggest_challenge IS 'Primary business challenges (can be multiple)'"
    )
    op.execute(
        "COMMENT ON COLUMN public.businesses.finance_tracking_method IS 'Current tools used for financial tracking'"
    )
    op.execute(
        "COMMENT ON COLUMN public.businesses.onboarding_notes IS 'Optional qualitative feedback provided during signup'"
    )

    op.create_table(
        "roles",
        sa.Column(
            "role_id", sa.BigInteger(), sa.Identity(always=False), nullable=False
        ),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["public.businesses.business_id"],
            name="roles_business_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("role_id", name="roles_pkey"),
        sa.UniqueConstraint(
            "business_id", "role_name", name="roles_business_id_role_name_key"
        ),
        schema="public",
    )

    op.create_table(
        "users",
        sa.Column(
            "user_id", sa.BigInteger(), sa.Identity(always=False), nullable=False
        ),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=150), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["public.businesses.business_id"],
            name="users_business_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["public.roles.role_id"], name="users_role_id_fkey"
        ),
        sa.PrimaryKeyConstraint("user_id", name="users_pkey"),
        sa.UniqueConstraint("email", name="users_email_key"),
        schema="public",
    )
    op.execute(
        "COMMENT ON COLUMN public.users.phone IS 'User contact number/WhatsApp collected during onboarding'"
    )

    op.create_table(
        "financial_records",
        sa.Column(
            "financial_record_id",
            sa.BigInteger(),
            sa.Identity(always=False),
            nullable=False,
        ),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("month", sa.Integer(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column(
            "total_revenue",
            sa.Numeric(14, 2),
            server_default=sa.text("0"),
            nullable=True,
        ),
        sa.Column(
            "total_expenses",
            sa.Numeric(14, 2),
            server_default=sa.text("0"),
            nullable=True,
        ),
        sa.Column("net_profit", sa.Numeric(14, 2), nullable=True),
        sa.Column("cash_balance", sa.Numeric(14, 2), nullable=True),
        sa.Column("loans_due", sa.Numeric(14, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "month >= 1 AND month <= 12", name="financial_records_month_check"
        ),
        sa.CheckConstraint("year >= 2000", name="financial_records_year_check"),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["public.businesses.business_id"],
            name="financial_records_business_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("financial_record_id", name="financial_records_pkey"),
        schema="public",
    )

    op.create_table(
        "daily_transactions",
        sa.Column(
            "transaction_id", sa.BigInteger(), sa.Identity(always=False), nullable=False
        ),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.CheckConstraint("amount >= 0", name="daily_transactions_amount_check"),
        sa.CheckConstraint(
            "type IN ('Revenue', 'Expense')", name="daily_transactions_type_check"
        ),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["public.businesses.business_id"],
            name="daily_transactions_business_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("transaction_id", name="daily_transactions_pkey"),
        schema="public",
    )

    op.create_table(
        "products",
        sa.Column(
            "product_id", sa.BigInteger(), sa.Identity(always=False), nullable=False
        ),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_name", sa.String(length=150), nullable=False),
        sa.Column("cost_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("selling_price", sa.Numeric(14, 2), nullable=True),
        sa.Column(
            "stock_quantity", sa.Integer(), server_default=sa.text("0"), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["public.businesses.business_id"],
            name="products_business_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("product_id", name="products_pkey"),
        schema="public",
    )

    op.create_table(
        "employees",
        sa.Column(
            "employee_id", sa.BigInteger(), sa.Identity(always=False), nullable=False
        ),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=True),
        sa.Column("role", sa.String(length=100), nullable=True),
        sa.Column("salary", sa.Numeric(14, 2), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "status IN ('Active', 'Left')", name="employees_status_check"
        ),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["public.businesses.business_id"],
            name="employees_business_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("employee_id", name="employees_pkey"),
        schema="public",
    )

    op.create_table(
        "decisions",
        sa.Column(
            "decision_id", sa.BigInteger(), sa.Identity(always=False), nullable=False
        ),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision_text", sa.Text(), nullable=True),
        sa.Column("decision_type", sa.String(length=50), nullable=True),
        sa.Column("decision_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("risk_level", sa.String(length=20), nullable=True),
        sa.Column("success_probability", sa.Numeric(5, 2), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "decision_type IN ('Marketing', 'Hiring', 'Pricing', 'Expansion')",
            name="decisions_decision_type_check",
        ),
        sa.CheckConstraint(
            "status IN ('Approved', 'Rejected', 'Modified')",
            name="decisions_status_check",
        ),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["public.businesses.business_id"],
            name="decisions_business_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("decision_id", name="decisions_pkey"),
        schema="public",
    )

    op.create_table(
        "decision_outcomes",
        sa.Column(
            "decision_outcome_id",
            sa.BigInteger(),
            sa.Identity(always=False),
            nullable=False,
        ),
        sa.Column("decision_id", sa.BigInteger(), nullable=False),
        sa.Column("actual_result", sa.Text(), nullable=True),
        sa.Column("profit_impact", sa.Numeric(14, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["decision_id"],
            ["public.decisions.decision_id"],
            name="decision_outcomes_decision_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("decision_outcome_id", name="decision_outcomes_pkey"),
        schema="public",
    )

    op.create_table(
        "alerts",
        sa.Column(
            "alert_id", sa.BigInteger(), sa.Identity(always=False), nullable=False
        ),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_type", sa.String(length=100), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "severity IN ('Low', 'Medium', 'High')", name="alerts_severity_check"
        ),
        sa.CheckConstraint(
            "status IN ('Active', 'Resolved')", name="alerts_status_check"
        ),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["public.businesses.business_id"],
            name="alerts_business_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("alert_id", name="alerts_pkey"),
        schema="public",
    )

    op.create_table(
        "business_health_scores",
        sa.Column(
            "health_score_id",
            sa.BigInteger(),
            sa.Identity(always=False),
            nullable=False,
        ),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("overall_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("cash_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("profitability_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("growth_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("cost_control_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("risk_score", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "calculated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["public.businesses.business_id"],
            name="business_health_scores_business_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("health_score_id", name="business_health_scores_pkey"),
        schema="public",
    )


def downgrade() -> None:
    op.drop_table("business_health_scores", schema="public")
    op.drop_table("alerts", schema="public")
    op.drop_table("decision_outcomes", schema="public")
    op.drop_table("decisions", schema="public")
    op.drop_table("employees", schema="public")
    op.drop_table("products", schema="public")
    op.drop_table("daily_transactions", schema="public")
    op.drop_table("financial_records", schema="public")
    op.drop_table("users", schema="public")
    op.drop_table("roles", schema="public")
    op.drop_table("businesses", schema="public")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
