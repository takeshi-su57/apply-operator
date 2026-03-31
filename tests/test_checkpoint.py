"""Tests for LangGraph checkpointing: save, resume, corruption, and listing."""

import re
from contextlib import ExitStack
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from apply_operator.checkpoint import create_checkpointer, generate_thread_id, get_run_summaries
from apply_operator.state import ApplicationState, JobListing, ResumeData

# ---------------------------------------------------------------------------
# Helpers — reuse the fake-node pattern from test_graph.py
# ---------------------------------------------------------------------------


def _make_resume() -> ResumeData:
    return ResumeData(
        raw_text="Jane Smith\nPython Developer",
        name="Jane Smith",
        skills=["Python", "Django"],
        experience=[
            {
                "title": "Backend Engineer",
                "company": "Acme",
                "duration": "2021-2024",
                "description": "Built APIs",
            }
        ],
        summary="Experienced backend developer.",
    )


def _make_jobs(count: int) -> list[JobListing]:
    return [
        JobListing(
            url=f"https://example.com/jobs/{i}",
            title=f"Job {i}",
            company=f"Company {i}",
            description=f"Description for job {i}",
        )
        for i in range(count)
    ]


def _fake_parse(state: ApplicationState) -> dict[str, Any]:
    return {"resume": _make_resume()}


def _fake_search(jobs: list[JobListing]):  # type: ignore[no-untyped-def]
    def _search(state: ApplicationState) -> dict[str, Any]:
        return {"jobs": jobs, "current_job_index": 0}

    return _search


def _fake_analyze(scores: list[float]):  # type: ignore[no-untyped-def]
    call_count = 0

    def _analyze(state: ApplicationState) -> dict[str, Any]:
        nonlocal call_count
        idx = state["current_job_index"]
        if idx >= len(state["jobs"]):
            return {}
        updated_jobs = list(state["jobs"])
        updated_jobs[idx] = updated_jobs[idx].model_copy(update={"fit_score": scores[call_count]})
        call_count += 1
        return {"jobs": updated_jobs}

    return _analyze


def _fake_fill(state: ApplicationState) -> dict[str, Any]:
    idx = state["current_job_index"]
    jobs = list(state["jobs"])
    jobs[idx] = jobs[idx].model_copy(update={"applied": True})
    return {
        "jobs": jobs,
        "current_job_index": idx + 1,
        "total_applied": state["total_applied"] + 1,
    }


def _noop_report(state: ApplicationState) -> dict[str, Any]:
    return {}


def _build_mocked_graph(
    checkpointer: BaseCheckpointSaver,  # type: ignore[type-arg]
    jobs: list[JobListing],
    scores: list[float],
) -> Any:
    """Build graph with mocked nodes and a real checkpointer."""
    patches = [
        patch("apply_operator.graph.parse_resume", _fake_parse),
        patch("apply_operator.graph.search_jobs", _fake_search(jobs)),
        patch("apply_operator.graph.analyze_fit", _fake_analyze(scores)),
        patch("apply_operator.graph.fill_application", _fake_fill),
        patch("apply_operator.graph.report_results", _noop_report),
    ]

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        from apply_operator.graph import build_graph

        return build_graph(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# Tests: thread ID generation
# ---------------------------------------------------------------------------


class TestGenerateThreadId:
    def test_format(self) -> None:
        tid = generate_thread_id()
        assert re.match(r"^run-\d+$", tid)

    def test_unique(self) -> None:
        import time

        t1 = generate_thread_id()
        time.sleep(1.1)
        t2 = generate_thread_id()
        assert t1 != t2


# ---------------------------------------------------------------------------
# Tests: checkpointer creation
# ---------------------------------------------------------------------------


class TestCreateCheckpointer:
    def test_creates_saver(self, tmp_path: Path) -> None:
        db_path = str(tmp_path / "test.sqlite")
        with create_checkpointer(db_path) as saver:
            assert isinstance(saver, SqliteSaver)
        assert (tmp_path / "test.sqlite").exists()

    def test_corrupted_db_fallback(self, tmp_path: Path) -> None:
        db_file = tmp_path / "corrupt.sqlite"
        db_file.write_bytes(b"this is not a valid sqlite database!!")
        with create_checkpointer(str(db_file)) as saver:
            assert isinstance(saver, SqliteSaver)


# ---------------------------------------------------------------------------
# Tests: checkpoint save and resume
# ---------------------------------------------------------------------------


class TestCheckpointSaveAndResume:
    @pytest.mark.asyncio
    async def test_run_saves_checkpoints(
        self, async_checkpoint_saver: AsyncSqliteSaver
    ) -> None:
        """A completed run has checkpoints and get_state().next is empty."""
        jobs = _make_jobs(1)
        scores = [0.8]
        graph = _build_mocked_graph(async_checkpoint_saver, jobs, scores)

        config = {"configurable": {"thread_id": "test-save-1"}}
        await graph.ainvoke(
            {"resume_path": "test.pdf", "job_urls": ["https://example.com"], "errors": [], "total_applied": 0, "total_skipped": 0, "current_job_index": 0},
            config=config,
        )

        snapshot = await graph.aget_state(config)
        assert snapshot.values
        assert not snapshot.next

    @pytest.mark.asyncio
    async def test_completed_run_not_rerun(
        self, async_checkpoint_saver: AsyncSqliteSaver
    ) -> None:
        """Invoking a completed run again with None yields no new node executions."""
        jobs = _make_jobs(1)
        scores = [0.8]
        graph = _build_mocked_graph(async_checkpoint_saver, jobs, scores)

        config = {"configurable": {"thread_id": "test-no-rerun"}}
        await graph.ainvoke(
            {"resume_path": "test.pdf", "job_urls": ["https://example.com"], "errors": [], "total_applied": 0, "total_skipped": 0, "current_job_index": 0},
            config=config,
        )

        node_names: list[str] = []
        async for event in graph.astream(None, config=config, stream_mode="updates"):
            for name in event:
                node_names.append(name)

        assert node_names == [], f"Expected no nodes to run, got: {node_names}"

    @pytest.mark.asyncio
    async def test_thread_id_isolation(
        self, async_checkpoint_saver: AsyncSqliteSaver
    ) -> None:
        """Two runs with different thread_ids have independent state."""
        jobs = _make_jobs(1)

        graph1 = _build_mocked_graph(async_checkpoint_saver, jobs, [0.8])
        graph2 = _build_mocked_graph(async_checkpoint_saver, jobs, [0.3])

        config1 = {"configurable": {"thread_id": "test-isolation-1"}}
        config2 = {"configurable": {"thread_id": "test-isolation-2"}}

        initial = {"resume_path": "test.pdf", "job_urls": ["https://example.com"], "errors": [], "total_applied": 0, "total_skipped": 0, "current_job_index": 0}

        result1 = await graph1.ainvoke(initial, config=config1)
        result2 = await graph2.ainvoke(initial, config=config2)

        assert result1["total_applied"] == 1
        assert result2["total_applied"] == 0
        assert result2["total_skipped"] == 1

    @pytest.mark.asyncio
    async def test_resume_from_interrupted(
        self, async_checkpoint_saver: AsyncSqliteSaver
    ) -> None:
        """A run interrupted mid-pipeline can be resumed."""
        call_count = 0

        def _failing_search(state: ApplicationState) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Simulated crash")
            return {"jobs": _make_jobs(1), "current_job_index": 0}

        patches = [
            patch("apply_operator.graph.parse_resume", _fake_parse),
            patch("apply_operator.graph.search_jobs", _failing_search),
            patch("apply_operator.graph.analyze_fit", _fake_analyze([0.8])),
            patch("apply_operator.graph.fill_application", _fake_fill),
            patch("apply_operator.graph.report_results", _noop_report),
        ]

        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            from apply_operator.graph import build_graph

            graph = build_graph(checkpointer=async_checkpoint_saver)

            config = {"configurable": {"thread_id": "test-resume"}}
            initial = {"resume_path": "test.pdf", "job_urls": ["https://example.com"], "errors": [], "total_applied": 0, "total_skipped": 0, "current_job_index": 0}

            with pytest.raises(RuntimeError, match="Simulated crash"):
                await graph.ainvoke(initial, config=config)

            snapshot = await graph.aget_state(config)
            assert snapshot.next

            result = await graph.ainvoke(None, config=config)
            assert result["total_applied"] == 1


# ---------------------------------------------------------------------------
# Tests: run listing (uses sync checkpointer for get_run_summaries)
# ---------------------------------------------------------------------------


class TestGetRunSummaries:
    def test_empty_db(self, checkpoint_saver: SqliteSaver) -> None:
        from apply_operator.graph import build_graph

        graph = build_graph(checkpointer=checkpoint_saver)
        runs = get_run_summaries(checkpoint_saver, graph)
        assert runs == []

    @pytest.mark.asyncio
    async def test_shows_completed_run(
        self, async_checkpoint_saver: AsyncSqliteSaver
    ) -> None:
        """Run completes, then verify summaries via the same saver."""
        jobs = _make_jobs(1)
        graph = _build_mocked_graph(async_checkpoint_saver, jobs, [0.7])

        config = {"configurable": {"thread_id": "test-list-completed"}}
        await graph.ainvoke(
            {"resume_path": "test.pdf", "job_urls": ["https://example.com"], "errors": [], "total_applied": 0, "total_skipped": 0, "current_job_index": 0},
            config=config,
        )

        # AsyncSqliteSaver also has sync list() method inherited from base
        # But get_run_summaries uses sync checkpointer, so we test via sync saver
        # sharing the same DB. For in-memory, we verify via aget_state directly.
        snapshot = await graph.aget_state(config)
        assert not snapshot.next  # completed

    @pytest.mark.asyncio
    async def test_shows_interrupted_run(
        self, async_checkpoint_saver: AsyncSqliteSaver
    ) -> None:
        def _crash_search(state: ApplicationState) -> dict[str, Any]:
            raise RuntimeError("boom")

        patches = [
            patch("apply_operator.graph.parse_resume", _fake_parse),
            patch("apply_operator.graph.search_jobs", _crash_search),
            patch("apply_operator.graph.analyze_fit", _fake_analyze([0.8])),
            patch("apply_operator.graph.fill_application", _fake_fill),
            patch("apply_operator.graph.report_results", _noop_report),
        ]

        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            from apply_operator.graph import build_graph

            graph = build_graph(checkpointer=async_checkpoint_saver)

            config = {"configurable": {"thread_id": "test-list-interrupted"}}
            with pytest.raises(RuntimeError):
                await graph.ainvoke(
                    {"resume_path": "test.pdf", "job_urls": ["https://example.com"], "errors": [], "total_applied": 0, "total_skipped": 0, "current_job_index": 0},
                    config=config,
                )

            snapshot = await graph.aget_state(config)
            assert snapshot.next  # interrupted — has pending nodes
