from __future__ import annotations

import uuid
import pytest
from unittest.mock import MagicMock

import sample_db_generator as sdbg


# -----------------------------------------------------------------------
# Shared helper
# -----------------------------------------------------------------------

def make_cursor(fetchone_return=None):
    cursor = MagicMock()
    cursor.fetchone.return_value = fetchone_return
    return cursor


# -----------------------------------------------------------------------
# create_business
# -----------------------------------------------------------------------

class TestCreateBusiness:

    def test_returns_valid_uuid(self):
        cursor = make_cursor()
        result = sdbg.create_business(cursor)
        uuid.UUID(result)  # raises ValueError if not a valid UUID

    def test_executes_insert_once(self):
        cursor = make_cursor()
        sdbg.create_business(cursor)
        assert cursor.execute.call_count == 1

    def test_inserts_correct_business_name_and_revenue(self):
        cursor = make_cursor()
        business_id = sdbg.create_business(cursor)
        _, params = cursor.execute.call_args[0]
        assert params[0] == business_id
        assert params[1] == "Urban Retail Store"
        assert params[4] == 250000

    def test_industry_is_from_known_list(self):
        cursor = make_cursor()
        sdbg.create_business(cursor)
        _, params = cursor.execute.call_args[0]
        assert params[2] in sdbg.industries

    def test_risk_appetite_is_valid(self):
        cursor = make_cursor()
        sdbg.create_business(cursor)
        _, params = cursor.execute.call_args[0]
        assert params[5] in sdbg.risk_levels

    def test_propagates_cursor_error(self):
        cursor = MagicMock()
        cursor.execute.side_effect = Exception("db down")
        with pytest.raises(Exception, match="db down"):
            sdbg.create_business(cursor)


# -----------------------------------------------------------------------
# create_roles_and_users
# -----------------------------------------------------------------------

class TestCreateRolesAndUsers:

    def test_executes_two_inserts_per_role(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = (1,)
        sdbg.create_roles_and_users(cursor, "biz-1")
        # 3 roles × 2 inserts (role + user) = 6
        assert cursor.execute.call_count == 6

    def test_returns_role_ids_from_fetchone(self):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [(10,), (20,), (30,)]
        role_ids = sdbg.create_roles_and_users(cursor, "biz-1")
        assert role_ids == [10, 20, 30]

    def test_role_description_matches_role_name(self):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [(1,), (2,), (3,)]
        sdbg.create_roles_and_users(cursor, "biz-1")
        for i, role in enumerate(sdbg.roles_list):
            _, params = cursor.execute.call_args_list[i * 2][0]
            assert params[1] == role
            assert params[2] == f"{role} role"

    def test_user_password_is_hashed_placeholder(self):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [(1,), (2,), (3,)]
        sdbg.create_roles_and_users(cursor, "biz-1")
        for i in range(len(sdbg.roles_list)):
            _, params = cursor.execute.call_args_list[i * 2 + 1][0]
            assert params[4] == "hashed_password"


# -----------------------------------------------------------------------
# create_products
# -----------------------------------------------------------------------

class TestCreateProducts:

    def test_default_count_is_8(self):
        cursor = make_cursor()
        sdbg.create_products(cursor, "biz-1")
        assert cursor.execute.call_count == 8

    def test_custom_count_respected(self):
        cursor = make_cursor()
        sdbg.create_products(cursor, "biz-1", count=3)
        assert cursor.execute.call_count == 3

    def test_selling_price_always_greater_than_cost(self):
        cursor = make_cursor()
        sdbg.create_products(cursor, "biz-1", count=20)
        for c in cursor.execute.call_args_list:
            _, params = c[0]
            assert params[3] > params[2]

    def test_product_name_is_from_known_list(self):
        cursor = make_cursor()
        sdbg.create_products(cursor, "biz-1", count=20)
        for c in cursor.execute.call_args_list:
            _, params = c[0]
            assert params[1] in sdbg.product_names

    def test_stock_quantity_within_valid_range(self):
        cursor = make_cursor()
        sdbg.create_products(cursor, "biz-1", count=20)
        for c in cursor.execute.call_args_list:
            _, params = c[0]
            assert 10 <= params[4] <= 200

    def test_zero_count_inserts_nothing(self):
        cursor = make_cursor()
        sdbg.create_products(cursor, "biz-1", count=0)
        cursor.execute.assert_not_called()


# -----------------------------------------------------------------------
# create_employees
# -----------------------------------------------------------------------

class TestCreateEmployees:

    def test_default_count_is_8(self):
        cursor = make_cursor()
        sdbg.create_employees(cursor, "biz-1")
        assert cursor.execute.call_count == 8

    def test_salary_within_valid_range(self):
        cursor = make_cursor()
        sdbg.create_employees(cursor, "biz-1", count=20)
        for c in cursor.execute.call_args_list:
            _, params = c[0]
            assert 20000 <= params[3] <= 80000

    def test_status_is_active_or_left(self):
        cursor = make_cursor()
        sdbg.create_employees(cursor, "biz-1", count=20)
        for c in cursor.execute.call_args_list:
            _, params = c[0]
            assert params[4] in {"Active", "Left"}

    def test_role_is_valid_value(self):
        cursor = make_cursor()
        sdbg.create_employees(cursor, "biz-1", count=20)
        for c in cursor.execute.call_args_list:
            _, params = c[0]
            assert params[2] in {"Sales", "Manager", "Support"}


# -----------------------------------------------------------------------
# create_daily_transactions
# -----------------------------------------------------------------------

class TestCreateDailyTransactions:

    def test_inserts_at_least_min_entries_per_day(self):
        cursor = make_cursor()
        sdbg.create_daily_transactions(cursor, "biz-1", days=2)
        # minimum 30 entries per day × 2 days = 60
        assert cursor.execute.call_count >= 60

    def test_transaction_type_is_revenue_or_expense(self):
        cursor = make_cursor()
        sdbg.create_daily_transactions(cursor, "biz-1", days=2)
        for c in cursor.execute.call_args_list:
            _, params = c[0]
            assert params[2] in {"Revenue", "Expense"}

    def test_revenue_uses_revenue_category(self):
        cursor = make_cursor()
        sdbg.create_daily_transactions(cursor, "biz-1", days=2)
        for c in cursor.execute.call_args_list:
            _, params = c[0]
            if params[2] == "Revenue":
                assert params[3] in sdbg.revenue_categories

    def test_expense_uses_expense_category(self):
        cursor = make_cursor()
        sdbg.create_daily_transactions(cursor, "biz-1", days=2)
        for c in cursor.execute.call_args_list:
            _, params = c[0]
            if params[2] == "Expense":
                assert params[3] in sdbg.expense_categories

    def test_zero_days_inserts_nothing(self):
        cursor = make_cursor()
        sdbg.create_daily_transactions(cursor, "biz-1", days=0)
        cursor.execute.assert_not_called()


# -----------------------------------------------------------------------
# create_financial_records
# -----------------------------------------------------------------------

class TestCreateFinancialRecords:

    def test_default_months_is_3(self):
        cursor = make_cursor()
        sdbg.create_financial_records(cursor, "biz-1")
        assert cursor.execute.call_count == 3

    def test_net_profit_equals_revenue_minus_expenses(self):
        cursor = make_cursor()
        sdbg.create_financial_records(cursor, "biz-1", months=5)
        for c in cursor.execute.call_args_list:
            _, params = c[0]
            revenue, expenses, net_profit = params[3], params[4], params[5]
            assert net_profit == revenue - expenses

    def test_custom_month_count_respected(self):
        cursor = make_cursor()
        sdbg.create_financial_records(cursor, "biz-1", months=6)
        assert cursor.execute.call_count == 6


# -----------------------------------------------------------------------
# create_decisions
# -----------------------------------------------------------------------

class TestCreateDecisions:

    def test_inserts_decision_and_outcome_per_entry(self):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [(i,) for i in range(1, 16)]
        sdbg.create_decisions(cursor, "biz-1", count=15)
        # 15 decisions + 15 outcomes = 30 calls
        assert cursor.execute.call_count == 30

    def test_returns_correct_decision_ids(self):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [(i,) for i in range(1, 6)]
        ids = sdbg.create_decisions(cursor, "biz-1", count=5)
        assert ids == [1, 2, 3, 4, 5]

    def test_decision_score_within_range(self):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [(i,) for i in range(1, 16)]
        sdbg.create_decisions(cursor, "biz-1", count=15)
        for c in cursor.execute.call_args_list[:15]:
            _, params = c[0]
            assert 1.0 <= params[3] <= 10.0

    def test_success_probability_within_range(self):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [(i,) for i in range(1, 16)]
        sdbg.create_decisions(cursor, "biz-1", count=15)
        for c in cursor.execute.call_args_list[:15]:
            _, params = c[0]
            assert 0.0 <= params[5] <= 1.0

    def test_decision_status_is_valid(self):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [(i,) for i in range(1, 16)]
        sdbg.create_decisions(cursor, "biz-1", count=15)
        for c in cursor.execute.call_args_list[:15]:
            _, params = c[0]
            assert params[6] in {"Approved", "Rejected", "Modified"}


# -----------------------------------------------------------------------
# create_alerts
# -----------------------------------------------------------------------

class TestCreateAlerts:

    def test_default_count_is_25(self):
        cursor = make_cursor()
        sdbg.create_alerts(cursor, "biz-1")
        assert cursor.execute.call_count == 25

    def test_alert_type_is_from_known_list(self):
        cursor = make_cursor()
        sdbg.create_alerts(cursor, "biz-1", count=10)
        for c in cursor.execute.call_args_list:
            _, params = c[0]
            assert params[1] in sdbg.alert_types

    def test_severity_is_valid(self):
        cursor = make_cursor()
        sdbg.create_alerts(cursor, "biz-1", count=10)
        for c in cursor.execute.call_args_list:
            _, params = c[0]
            assert params[2] in {"Low", "Medium", "High"}

    def test_status_is_active_or_resolved(self):
        cursor = make_cursor()
        sdbg.create_alerts(cursor, "biz-1", count=10)
        for c in cursor.execute.call_args_list:
            _, params = c[0]
            assert params[4] in {"Active", "Resolved"}

    def test_zero_count_inserts_nothing(self):
        cursor = make_cursor()
        sdbg.create_alerts(cursor, "biz-1", count=0)
        cursor.execute.assert_not_called()


# -----------------------------------------------------------------------
# create_health_scores
# -----------------------------------------------------------------------

class TestCreateHealthScores:

    def test_default_count_is_15(self):
        cursor = make_cursor()
        sdbg.create_health_scores(cursor, "biz-1")
        assert cursor.execute.call_count == 15

    def test_all_six_scores_within_range(self):
        cursor = make_cursor()
        sdbg.create_health_scores(cursor, "biz-1", count=15)
        for c in cursor.execute.call_args_list:
            _, params = c[0]
            for score in params[1:]:  # skip business_id at params[0]
                assert 1.0 <= score <= 10.0

    def test_inserts_seven_params(self):
        # business_id + 6 score columns
        cursor = make_cursor()
        sdbg.create_health_scores(cursor, "biz-1", count=1)
        _, params = cursor.execute.call_args[0]
        assert len(params) == 7


# -----------------------------------------------------------------------
# run_all
# -----------------------------------------------------------------------

class TestRunAll:

    def _make_conn(self):
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (1,)
        conn.cursor.return_value = cursor
        return conn, cursor

    def test_commits_once_per_section(self):
        conn, _ = self._make_conn()
        sdbg.run_all(conn)
        # 9 sections: business, roles, products, employees,
        # transactions, financial, decisions, alerts, health
        assert conn.commit.call_count == 9

    def test_closes_cursor_and_connection(self):
        conn, cursor = self._make_conn()
        sdbg.run_all(conn)
        cursor.close.assert_called_once()
        conn.close.assert_called_once()

    def test_prints_success_message(self, capsys):
        conn, _ = self._make_conn()
        sdbg.run_all(conn)
        out = capsys.readouterr().out
        assert "✅" in out
        assert "Single business data inserted successfully" in out

    def test_connection_error_propagates(self):
        conn = MagicMock()
        conn.cursor.side_effect = Exception("cannot connect")
        with pytest.raises(Exception, match="cannot connect"):
            sdbg.run_all(conn)

    def test_cursor_execute_error_propagates(self):
        conn = MagicMock()
        cursor = MagicMock()
        cursor.execute.side_effect = Exception("table missing")
        conn.cursor.return_value = cursor
        with pytest.raises(Exception, match="table missing"):
            sdbg.run_all(conn)
