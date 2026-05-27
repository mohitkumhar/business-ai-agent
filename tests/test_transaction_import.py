from __future__ import annotations

from datetime import date, datetime

import pytest

from agent_code import transaction_import


def test_norm_header_and_find_col_handle_case_spaces_and_symbols():
    headers = [" Transaction Date ", "Dr/Cr", "Total Amount"]

    assert transaction_import._norm_header(" Total Amount ($) ") == "total_amount"
    assert transaction_import._find_col(headers, ("transaction_date", "date")) == 0
    assert transaction_import._find_col(headers, ("dr_cr", "type")) == 1
    assert transaction_import._find_col(headers, ("missing",)) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2026-05-27T10:15:00", date(2026, 5, 27)),
        ("27/05/2026", date(2026, 5, 27)),
        ("27-05-2026", date(2026, 5, 27)),
        ("05/27/2026", date(2026, 5, 27)),
        ("2026/05/27", date(2026, 5, 27)),
        ("45000", date(2023, 3, 15)),
        (datetime(2026, 5, 27, 1, 2, 3), date(2026, 5, 27)),
        (date(2026, 5, 27), date(2026, 5, 27)),
    ],
)
def test_parse_date_supported_formats(raw, expected):
    assert transaction_import._parse_date(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "   ", "not-a-date", "1000"])
def test_parse_date_returns_none_for_missing_or_invalid_values(raw):
    assert transaction_import._parse_date(raw) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (123, 123.0),
        (12.5, 12.5),
        ("$1,234.50", 1234.5),
        ("-99.95", -99.95),
    ],
)
def test_parse_amount_supported_values(raw, expected):
    assert transaction_import._parse_amount(raw) == expected


@pytest.mark.parametrize("raw", [None, "", " ", "abc"])
def test_parse_amount_returns_none_for_missing_or_invalid_values(raw):
    assert transaction_import._parse_amount(raw) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Revenue", "Revenue"),
        ("credit", "Revenue"),
        ("sales return", "Revenue"),
        ("Expense", "Expense"),
        ("dr", "Expense"),
        ("cost of goods", "Expense"),
    ],
)
def test_parse_type_supported_values(raw, expected):
    assert transaction_import._parse_type(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "transfer"])
def test_parse_type_returns_none_for_unknown_values(raw):
    assert transaction_import._parse_type(raw) is None


def test_parse_csv_bytes_maps_aliases_skips_invalid_rows_and_truncates_text():
    long_category = "c" * 150
    long_description = "d" * 600
    raw = (
        "\ufeffTxn Date,Dr/Cr,Cat,Amt,Memo\n"
        f"2026-05-27,credit,{long_category},123.45,{long_description}\n"
        "2026-05-28,,Refunds,-20.00,\n"
        "bad-date,expense,Ignored,10.00,invalid date\n"
        ",,,,blank row\n"
    ).encode("utf-8")

    rows = transaction_import.parse_csv_bytes(raw)

    assert rows == [
        (date(2026, 5, 27), "Revenue", "c" * 100, 123.45, "d" * 500),
        (date(2026, 5, 28), "Expense", "Refunds", 20.0, "Refunds"),
    ]


def test_parse_csv_bytes_requires_header_and_data_row():
    with pytest.raises(ValueError, match="header row"):
        transaction_import.parse_csv_bytes(b"date,amount\n")


def test_rows_from_dicts_requires_date_and_amount_columns():
    with pytest.raises(ValueError, match="required columns"):
        transaction_import._rows_from_dicts(["date", "category"], [["2026-05-27", "Sales"]])


def test_rows_from_dicts_raises_when_all_rows_invalid():
    with pytest.raises(ValueError, match="No valid data rows"):
        transaction_import._rows_from_dicts(
            ["date", "amount"],
            [["bad-date", "12.00"], ["2026-05-27", "not-money"]],
        )


def test_parse_xlsx_bytes_reads_active_sheet_when_openpyxl_is_available():
    openpyxl = pytest.importorskip("openpyxl")
    from io import BytesIO

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Date", "Type", "Category", "Amount", "Description"])
    ws.append([date(2026, 5, 27), "Expense", "Supplies", 42, "Paper"])
    bio = BytesIO()
    wb.save(bio)

    assert transaction_import.parse_xlsx_bytes(bio.getvalue()) == [
        (date(2026, 5, 27), "Expense", "Supplies", 42.0, "Paper")
    ]
