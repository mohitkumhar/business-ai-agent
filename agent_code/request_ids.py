from __future__ import annotations

import re
from uuid import uuid4


REQUEST_ID_MAX_LENGTH = 64
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


def normalize_request_id(request_id: str | None) -> str | None:
    if request_id is None:
        return None

    candidate = request_id.strip()
    if not candidate or len(candidate) > REQUEST_ID_MAX_LENGTH:
        return None
    if not REQUEST_ID_PATTERN.fullmatch(candidate):
        return None
    return candidate


def get_request_id(*candidates: str | None) -> str:
    for candidate in candidates:
        normalized = normalize_request_id(candidate)
        if normalized:
            return normalized
    return uuid4().hex