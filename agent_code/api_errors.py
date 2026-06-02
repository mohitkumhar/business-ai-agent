from __future__ import annotations

from uuid import uuid4

from flask import jsonify
from flask import g

from logger.logger import logger


SAFE_INTERNAL_ERROR_MESSAGE = "An internal server error occurred. Please try again later."


def _ensure_request_id() -> str:
    try:
        request_id = getattr(g, "request_id", None)
    except RuntimeError:
        request_id = None

    if not request_id:
        request_id = uuid4().hex
        try:
            g.request_id = request_id
        except RuntimeError:
            pass

    return str(request_id)


def internal_error_response(exc: BaseException | None = None, *, field: str = "error"):
    request_id = _ensure_request_id()
    if exc is not None:
        logger.error("Unhandled API exception [request_id=%s]: %s", request_id, exc, exc_info=True)
    response = jsonify({field: SAFE_INTERNAL_ERROR_MESSAGE})
    response.headers["X-Request-ID"] = request_id
    return response, 500
