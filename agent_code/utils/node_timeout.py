"""Synchronous timeout wrapper for blocking node / graph calls (Flask is sync)."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from typing import Callable, TypeVar

from logger.logger import logger

T = TypeVar("T")

MAX_NODE_TIMEOUT_SECONDS = 30


def run_with_timeout(fn: Callable[[], T], timeout_seconds: float = MAX_NODE_TIMEOUT_SECONDS) -> T:
    """
    Run ``fn`` in a worker thread and return its result, or raise TimeoutError.
    Use for graph.invoke in chained steps; streaming uses client-side watchdogs.
    """
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(fn)
        try:
            return future.result(timeout=timeout_seconds)
        except FuturesTimeout:
            logger.error("[TIMEOUT] Node callable exceeded %ss", timeout_seconds)
            raise TimeoutError(
                f"This request took too long (>{timeout_seconds}s). Please try again."
            ) from None
