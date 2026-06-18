from __future__ import annotations
import uuid

from flask import jsonify
from flask import g

from logger.logger import logger
from request_ids import get_request_id


SAFE_INTERNAL_ERROR_MESSAGE = "An internal server error occurred. Please try again later."

def internal_error_response(exc: BaseException | None = None, *, field: str = "error"):
    request_id = str(uuid.uuid4())[:8]
    if exc is not None:
        logger.error("[request_id=%s] Unhandled API exception: %s", request_id, exc, exc_info=True)
    return jsonify({field: SAFE_INTERNAL_ERROR_MESSAGE, "request_id": request_id}), 500
