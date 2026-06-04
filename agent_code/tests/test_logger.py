from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import pytest

AGENT_CODE_DIR = Path(__file__).resolve().parents[1]
if str(AGENT_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_CODE_DIR))


# ── Import logger module ───────────────────────────────────────
from logger.logger import logger


# ── Normal behavior ────────────────────────────────────────────
def test_logger_name():
    assert logger.name == "intelligent_ai_agent"


def test_logger_level():
    assert logger.getEffectiveLevel() in (logging.INFO, logging.WARNING)


def test_logger_info(caplog):
    with caplog.at_level(logging.INFO, logger="intelligent_ai_agent"):
        logger.info("test info message")
    assert "test info message" in caplog.text


def test_logger_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="intelligent_ai_agent"):
        logger.warning("test warning message")
    assert "test warning message" in caplog.text


def test_logger_error(caplog):
    with caplog.at_level(logging.ERROR, logger="intelligent_ai_agent"):
        logger.error("test error message")
    assert "test error message" in caplog.text


# ── Edge cases ─────────────────────────────────────────────────
def test_logger_empty_message(caplog):
    with caplog.at_level(logging.INFO, logger="intelligent_ai_agent"):
        logger.info("")
    assert "" in caplog.text


def test_logger_special_characters(caplog):
    with caplog.at_level(logging.INFO, logger="intelligent_ai_agent"):
        logger.info("special chars: !@#$%^&*()")
    assert "special chars: !@#$%^&*()" in caplog.text


def test_logger_long_message(caplog):
    long_msg = "a" * 10000
    with caplog.at_level(logging.INFO, logger="intelligent_ai_agent"):
        logger.info(long_msg)
    assert long_msg in caplog.text


# ── Failure paths ──────────────────────────────────────────────
def test_logger_is_not_none():
    assert logger is not None


def test_logger_has_handlers():
    root_logger = logging.getLogger()
    assert len(root_logger.handlers) > 0


def test_log_file_exists():
    log_file = AGENT_CODE_DIR / "logs" / "app.log"
    assert log_file.exists()