import pytest
from datetime import date
import agent_code.ocr_processor
from agent_code.ocr_processor import extract_transactions_from_image

def test_extract_transactions_from_image_fenced_json(monkeypatch):
    """Test that fenced JSON is correctly parsed."""
    monkeypatch.setattr(agent_code.ocr_processor, "GEMINI_API_KEY", "dummy_key")
    
    mock_response_text = '```json\n[{"date": "2026-03-01", "type": "Revenue", "category": "Sales", "amount": 100, "description": "Test"}]\n```'
    
    class MockResponse:
        def json(self):
            return {
                "candidates": [{
                    "content": {
                        "parts": [{"text": mock_response_text}]
                    }
                }]
            }
        def raise_for_status(self):
            pass
            
    import requests
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: MockResponse())
    
    results = extract_transactions_from_image(b"fake_image", "test.png")
    assert len(results) == 1
    assert results[0] == (date(2026, 3, 1), "Revenue", "Sales", 100.0, "Test")

def test_extract_transactions_from_image_unfenced_json(monkeypatch):
    """Test that raw unfenced JSON is correctly parsed."""
    monkeypatch.setattr(agent_code.ocr_processor, "GEMINI_API_KEY", "dummy_key")
    
    mock_response_text = '[{"date": "2026-03-02", "type": "Expense", "category": "Rent", "amount": 500, "description": "Shop rent"}]'
    
    class MockResponse:
        def json(self):
            return {
                "candidates": [{
                    "content": {
                        "parts": [{"text": mock_response_text}]
                    }
                }]
            }
        def raise_for_status(self):
            pass
            
    import requests
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: MockResponse())
    
    results = extract_transactions_from_image(b"fake_image", "test.png")
    assert len(results) == 1
    assert results[0] == (date(2026, 3, 2), "Expense", "Rent", 500.0, "Shop rent")

def test_extract_transactions_from_image_embedded_json(monkeypatch):
    """Test that JSON embedded in text is correctly parsed."""
    monkeypatch.setattr(agent_code.ocr_processor, "GEMINI_API_KEY", "dummy_key")
    
    mock_response_text = 'Here is the data: [{"date": "2026-03-03", "type": "Revenue", "category": "Sales", "amount": 200, "description": "Embedded"}] hope this helps!'
    
    class MockResponse:
        def json(self):
            return {
                "candidates": [{
                    "content": {
                        "parts": [{"text": mock_response_text}]
                    }
                }]
            }
        def raise_for_status(self):
            pass
            
    import requests
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: MockResponse())
    
    results = extract_transactions_from_image(b"fake_image", "test.png")
    assert len(results) == 1
    assert results[0] == (date(2026, 3, 3), "Revenue", "Sales", 200.0, "Embedded")
