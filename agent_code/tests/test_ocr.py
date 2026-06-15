import os
import json
import pytest
from datetime import date
from unittest.mock import patch, MagicMock

# Set API key environment variable before importing ocr_processor to allow normal initialization
os.environ["GEMINI_API_KEY"] = "mock-api-key"

import ocr_processor
from ocr_processor import extract_transactions_from_image


def test_ocr_missing_api_key():
    # Force GEMINI_API_KEY to be empty
    with patch("ocr_processor.GEMINI_API_KEY", None):
        with pytest.raises(ValueError, match="Missing GEMINI_API_KEY"):
            extract_transactions_from_image(b"dummy_bytes", "test.jpg")


@patch("requests.post")
def test_ocr_success_path(mock_post):
    # Mock successful response from Gemini with matching schema
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps([
                                {
                                    "date": "2026-06-15",
                                    "type": "Revenue",
                                    "category": "Sales",
                                    "amount": 1500.0,
                                    "description": "Daily store sales"
                                },
                                {
                                    "date": "2026-06-14",
                                    "type": "Expense",
                                    "category": "Rent",
                                    "amount": 500.0,
                                    "description": "Monthly rent payment"
                                }
                            ])
                        }
                    ]
                }
            }
        ]
    }
    mock_post.return_value = mock_response

    results = extract_transactions_from_image(b"fake_image_bytes", "test.png")
    
    assert len(results) == 2
    assert results[0] == (date(2026, 6, 15), "Revenue", "Sales", 1500.0, "Daily store sales")
    assert results[1] == (date(2026, 6, 14), "Expense", "Rent", 500.0, "Monthly rent payment")

    # Verify requests.post payload structure (especially generationConfig and responseSchema)
    args, kwargs = mock_post.call_args
    payload = kwargs["json"]
    assert "generationConfig" in payload
    assert payload["generationConfig"]["responseMimeType"] == "application/json"
    assert "responseSchema" in payload["generationConfig"]
    assert payload["generationConfig"]["responseSchema"]["type"] == "ARRAY"


@patch("requests.post")
def test_ocr_api_failure_status(mock_post):
    # Mock non-200 HTTP response
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = Exception("HTTP 500 Server Error")
    mock_post.return_value = mock_response

    with pytest.raises(Exception):
        extract_transactions_from_image(b"fake_image_bytes", "test.png")


@patch("requests.post")
def test_ocr_malformed_json_fallback(mock_post):
    # Mock success status but returned JSON is corrupted
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": "{invalid-json-structure}"
                        }
                    ]
                }
            }
        ]
    }
    mock_post.return_value = mock_response

    with pytest.raises(ValueError, match="AI returned unreadable data"):
        extract_transactions_from_image(b"fake_image_bytes", "test.png")


@patch("requests.post")
def test_ocr_invalid_schema_structure(mock_post):
    # Mock response returning object instead of list
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({"status": "not-a-list"})
                        }
                    ]
                }
            }
        ]
    }
    mock_post.return_value = mock_response

    with pytest.raises(ValueError, match="Gemini returned an object instead of a list"):
        extract_transactions_from_image(b"fake_image_bytes", "test.png")
