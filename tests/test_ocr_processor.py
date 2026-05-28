from __future__ import annotations

from datetime import date

import pytest

from agent_code import ocr_processor


class _FakeResponse:
    def __init__(self, text: str):
        self._text = text

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": self._text,
                            }
                        ]
                    }
                }
            ]
        }


@pytest.mark.parametrize(
    "gemini_text",
    [
        '[{"date": "2026-03-01", "type": "Revenue", "category": "Sales", "amount": 1500, "description": "Cash sale"}]',
        '```json\n[{"date": "2026-03-01", "type": "Revenue", "category": "Sales", "amount": 1500, "description": "Cash sale"}]\n```',
        'Here is the data:\n[{"date": "2026-03-01", "type": "Revenue", "category": "Sales", "amount": 1500, "description": "Cash sale"}]\nDone.',
    ],
)
def test_extract_transactions_from_image_parses_raw_and_wrapped_json(
    monkeypatch, gemini_text
):
    monkeypatch.setattr(ocr_processor, "GEMINI_API_KEY", "unit-test-key")
    monkeypatch.setattr(
        ocr_processor.requests,
        "post",
        lambda *args, **kwargs: _FakeResponse(gemini_text),
    )

    transactions = ocr_processor.extract_transactions_from_image(
        b"image-bytes", "ledger.png"
    )

    assert transactions == [
        (date(2026, 3, 1), "Revenue", "Sales", 1500.0, "Cash sale"),
    ]


def test_clean_gemini_json_response_ignores_unclosed_code_fence():
    raw_json = '[{"date": "2026-03-01", "amount": 1500}]'

    assert ocr_processor._clean_gemini_json_response(f"```json\n{raw_json}") == raw_json
