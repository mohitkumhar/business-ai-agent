from __future__ import annotations

from flask import jsonify

from logger.logger import logger


SAFE_INTERNAL_ERROR_MESSAGE = "An internal server error occurred. Please try again later."


def safe_error_text(exc: BaseException | None = None, context: str = "") -> str:
    """Return a user-safe error string. Never expose exception details."""
    logger.error("Unhandled exception%s: %s", f" ({context})" if context else "", exc, exc_info=True)
    return SAFE_INTERNAL_ERROR_MESSAGE


def internal_error_response(exc: BaseException | None = None, *, field: str = "error"):
    if exc is not None:
        logger.error("Unhandled API exception: %s", exc, exc_info=True)
    return jsonify({field: SAFE_INTERNAL_ERROR_MESSAGE}), 500
