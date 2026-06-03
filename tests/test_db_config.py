from __future__ import annotations

import pytest

from agent_code import db_config


@pytest.mark.parametrize(
    ("sql", "expected"),
    [
        ("SELECT * FROM businesses;", "SELECT * FROM businesses"),
        ("  with recent as (select 1) select * from recent  ", "with recent as (select 1) select * from recent"),
    ],
)
def test_assert_read_only_select_accepts_single_selects(sql, expected):
    assert db_config._assert_read_only_select(sql) == expected


@pytest.mark.parametrize(
    "sql",
    [
        "",
        "UPDATE users SET role = 'admin'",
        "DELETE FROM users",
        "SELECT * FROM users; SELECT * FROM roles",
        "WITH changed AS (UPDATE users SET role = 'admin' RETURNING *) SELECT * FROM changed",
    ],
)
def test_assert_read_only_select_rejects_unsafe_sql(sql):
    with pytest.raises(ValueError):
        db_config._assert_read_only_select(sql)


def test_execute_read_query_params_uses_sanitized_sql_and_params(monkeypatch):
    class FakeCursor:
        def __init__(self):
            self.executed = None
            self.closed = False

        def execute(self, sql, params):
            self.executed = (sql, params)

        def fetchall(self):
            return [{"business_id": "b-1"}]

        def close(self):
            self.closed = True

    class FakeConnection:
        def __init__(self):
            self.cursor_obj = FakeCursor()
            self.closed = False

        def cursor(self, cursor_factory=None):
            self.cursor_factory = cursor_factory
            return self.cursor_obj

        def close(self):
            self.closed = True

    conn = FakeConnection()
    monkeypatch.setattr(db_config, "get_db_connection", lambda: conn)

    rows = db_config.execute_read_query_params(
        "SELECT * FROM businesses WHERE business_id = %s;",
        ["b-1"],
    )

    assert rows == [{"business_id": "b-1"}]
    assert conn.cursor_obj.executed == (
        "SELECT * FROM businesses WHERE business_id = %s",
        ["b-1"],
    )
    assert conn.cursor_obj.closed is True
    assert conn.closed is True


def test_execute_read_query_params_wraps_database_errors(monkeypatch):
    class FailingCursor:
        def execute(self, sql, params):
            raise RuntimeError("db down")

        def close(self):
            pass

    class FakeConnection:
        def cursor(self, cursor_factory=None):
            return FailingCursor()

        def close(self):
            self.closed = True

    monkeypatch.setattr(db_config, "get_db_connection", lambda: FakeConnection())

    with pytest.raises(RuntimeError, match="SQL execution failed"):
        db_config.execute_read_query_params("SELECT * FROM businesses")