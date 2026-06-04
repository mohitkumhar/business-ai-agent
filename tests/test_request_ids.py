from __future__ import annotations

import re

from agent_code.request_ids import get_request_id, normalize_request_id


def test_normalize_request_id_accepts_constrained_values():
    assert normalize_request_id("req-123_abc.DEF") == "req-123_abc.DEF"


def test_normalize_request_id_rejects_blank_invalid_and_long_values():
    assert normalize_request_id("   ") is None
    assert normalize_request_id("bad\r\nrequest-id") is None
    assert normalize_request_id("x" * 65) is None


def test_get_request_id_falls_back_to_generated_uuid_for_invalid_values():
    request_id = get_request_id("bad\r\nrequest-id")

    assert re.fullmatch(r"[0-9a-f]{32}", request_id)


def test_get_request_id_prefers_the_first_valid_candidate():
    assert get_request_id("bad\r\nrequest-id", " req-keep-me ") == "req-keep-me"