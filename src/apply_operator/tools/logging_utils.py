"""Logging utilities for LangGraph node instrumentation."""

import functools
import inspect
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


def log_node(func: Any) -> Any:
    """Decorator that logs node entry, exit, and duration.

    Works with both sync and async node functions.
    Logs at INFO level on success, ERROR on exception.
    The exception is re-raised after logging.
    """
    node_name = func.__name__

    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(state: Any) -> dict[str, Any]:
            logger.info("node=%s | started", node_name)
            start = time.perf_counter()
            try:
                result: dict[str, Any] = await func(state)
                elapsed = time.perf_counter() - start
                logger.info("node=%s | completed | %.2fs", node_name, elapsed)
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start
                logger.error(
                    "node=%s | failed | %.2fs | %s: %s",
                    node_name, elapsed, type(e).__name__, e,
                )
                raise

        return async_wrapper

    @functools.wraps(func)
    def sync_wrapper(state: Any) -> dict[str, Any]:
        logger.info("node=%s | started", node_name)
        start = time.perf_counter()
        try:
            result: dict[str, Any] = func(state)
            elapsed = time.perf_counter() - start
            logger.info("node=%s | completed | %.2fs", node_name, elapsed)
            return result
        except Exception as e:
            elapsed = time.perf_counter() - start
            logger.error(
                "node=%s | failed | %.2fs | %s: %s",
                node_name, elapsed, type(e).__name__, e,
            )
            raise

    return sync_wrapper
