import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_TABLES = {
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
}

EXPECTED_COLUMNS = {
    "businesses": {
        "business_id",
        "business_name",
        "industry_type",
        "owner_name",
        "monthly_target_revenue",
        "risk_appetite",
        "created_at",
        "updated_at",
        "city",
        "business_age",
        "employees_range",
        "biggest_challenge",
        "finance_tracking_method",
        "onboarding_notes",
    },
    "users": {
        "user_id",
        "business_id",
        "role_id",
        "name",
        "email",
        "password_hash",
        "created_at",
        "phone",
    },
}


def _alembic_config(database_url: str) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def test_alembic_project_files_are_present():
    assert (PROJECT_ROOT / "alembic.ini").is_file()
    assert (PROJECT_ROOT / "alembic" / "env.py").is_file()
    assert list((PROJECT_ROOT / "alembic" / "versions").glob("*.py"))


def test_sqlalchemy_metadata_tracks_current_business_schema():
    from agent_code.db_metadata import metadata

    assert EXPECTED_TABLES <= set(metadata.tables)
    for table_name, expected_columns in EXPECTED_COLUMNS.items():
        table = metadata.tables[table_name]
        assert expected_columns <= set(table.columns.keys())


def test_alembic_upgrade_head_creates_current_schema():
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to run the migration against PostgreSQL")

    engine = create_engine(database_url)
    config = _alembic_config(database_url)

    try:
        with engine.begin() as connection:
            connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))

        command.upgrade(config, "head")

        inspector = inspect(engine)
        assert EXPECTED_TABLES <= set(inspector.get_table_names(schema="public"))
        for table_name, expected_columns in EXPECTED_COLUMNS.items():
            columns = {
                column["name"]
                for column in inspector.get_columns(table_name, schema="public")
            }
            assert expected_columns <= columns

        with engine.connect() as connection:
            version = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
        assert version == "20260528_0001"
    finally:
        with engine.begin() as connection:
            connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
        engine.dispose()
