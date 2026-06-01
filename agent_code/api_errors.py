from __future__ import annotations

from flask import jsonify

from logger.logger import logger
import uuid


SAFE_INTERNAL_ERROR_MESSAGE = "An internal server error occurred. Please try again later."




def internal_error_response(exc: BaseException | None = None, *, field: str = "error"):
    request_id = str(uuid.uuid4())
    if exc is not None:
        logger.error("Unhandled API exception [%s]: %s", request_id, exc, exc_info=True)
    return jsonify({
        field: SAFE_INTERNAL_ERROR_MESSAGE,
        "request_id": request_id
    }), 500
