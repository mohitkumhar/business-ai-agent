from __future__ import annotations

from flask import jsonify
from flask import g

from logger.logger import logger
from request_ids import get_request_id


SAFE_INTERNAL_ERROR_MESSAGE = "An internal server error occurred. Please try again later."


def internal_error_response(exc: BaseException | None = None, *, field: str = "error"):
    try:
        request_id = get_request_id(getattr(g, "request_id", None))
    except RuntimeError:
        request_id = get_request_id()
    try:
        g.request_id = request_id
    except RuntimeError:
        pass
    if exc is not None:
        logger.error("Unhandled API exception [request_id=%s]: %s", request_id, exc, exc_info=True)
    response = jsonify({field: SAFE_INTERNAL_ERROR_MESSAGE})
    response.headers["X-Request-ID"] = request_id
    return response, 500
