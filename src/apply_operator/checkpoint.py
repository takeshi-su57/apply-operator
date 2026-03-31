"""Checkpoint management for run persistence and resumption."""

import logging
import sqlite3
import time
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Any

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from apply_operator.config import get_settings

logger = logging.getLogger(__name__)


def generate_thread_id() -> str:
    """Generate a unique thread ID for a new run."""
    return f"run-{int(time.time())}"


def _resolve_db_path(db_path: str | None = None) -> Path:
    """Resolve and ensure parent directory for checkpoint DB."""
    path = Path(db_path or get_settings().checkpoint_db)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@asynccontextmanager
async def create_async_checkpointer(
    db_path: str | None = None,
) -> AsyncIterator[AsyncSqliteSaver]:
    """Create an AsyncSqliteSaver for use with async graph execution.

    Handles corrupted DB gracefully by falling back to in-memory SQLite.
    """
    resolved = _resolve_db_path(db_path)
    try:
        async with AsyncSqliteSaver.from_conn_string(str(resolved)) as saver:
            await saver.setup()
            yield saver
    except sqlite3.DatabaseError as exc:
        logger.warning("Checkpoint DB corrupted (%s), using in-memory fallback", exc)
        async with AsyncSqliteSaver.from_conn_string(":memory:") as saver:
            await saver.setup()
            yield saver


@contextmanager
def create_checkpointer(db_path: str | None = None) -> Iterator[SqliteSaver]:
    """Create a sync SqliteSaver for non-streaming operations (list-runs, get_state).

    Handles corrupted DB gracefully by falling back to in-memory SQLite.
    """
    resolved = _resolve_db_path(db_path)
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(str(resolved), check_same_thread=False)
        saver = SqliteSaver(conn)
        saver.setup()
        yield saver
    except sqlite3.DatabaseError as exc:
        logger.warning("Checkpoint DB corrupted (%s), using in-memory fallback", exc)
        conn = sqlite3.connect(":memory:")
        saver = SqliteSaver(conn)
        saver.setup()
        yield saver
    finally:
        if conn is not None:
            conn.close()


def get_run_summaries(
    checkpointer: SqliteSaver,
    graph: Any,
) -> list[dict[str, Any]]:
    """Query checkpoint DB and return summary of all thread runs.

    Returns list of dicts with: thread_id, status, step, next_node.
    """
    threads: dict[str, dict[str, Any]] = {}
    try:
        for cp_tuple in checkpointer.list(None):
            tid = cp_tuple.config["configurable"]["thread_id"]
            if tid not in threads:
                meta = cp_tuple.metadata or {}
                threads[tid] = {
                    "thread_id": tid,
                    "step": meta.get("step", 0),
                    "timestamp": cp_tuple.checkpoint.get("ts", ""),
                }
    except sqlite3.DatabaseError:
        logger.warning("Cannot read checkpoint DB for listing runs")
        return []

    runs: list[dict[str, Any]] = []
    for tid, info in threads.items():
        config = {"configurable": {"thread_id": tid}}
        try:
            snapshot = graph.get_state(config)
            if not snapshot.next:
                info["status"] = "completed"
                info["next_node"] = None
            else:
                info["status"] = "interrupted"
                info["next_node"] = ", ".join(snapshot.next)
        except Exception:
            info["status"] = "unknown"
            info["next_node"] = None
        runs.append(info)

    return runs
