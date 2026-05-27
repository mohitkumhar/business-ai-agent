from __future__ import annotations

from io import BytesIO

from .helpers import FakeConnection, FakeCursor


def test_import_transactions_requires_file(client, auth_headers):
    response = client.post("/api/v1/import/transactions", headers=auth_headers)

    assert response.status_code == 400
    assert response.get_json()["error"] == "No file part"


def test_import_transactions_rejects_unsupported_file_type(client, auth_headers):
    response = client.post(
        "/api/v1/import/transactions",
        headers=auth_headers,
        data={"file": (BytesIO(b"hello"), "transactions.txt")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Unsupported file format"


def test_import_transactions_parses_csv_and_inserts_rows(client, app_module, auth_headers, monkeypatch):
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    monkeypatch.setattr(
        app_module,
        "parse_csv_bytes",
        lambda raw: [("2026-05-20", "Revenue", "Sales", 1250.0, "Counter sale")],
    )
    monkeypatch.setattr(app_module, "get_db_connection", lambda: connection)

    response = client.post(
        "/api/v1/import/transactions",
        headers=auth_headers,
        data={"file": (BytesIO(b"date,type,amount\n2026-05-20,Revenue,1250"), "transactions.csv")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    assert response.get_json() == {"message": "Successfully imported 1 transactions!"}
    assert connection.committed is True
    assert connection.closed is True
    assert cursor.executed
