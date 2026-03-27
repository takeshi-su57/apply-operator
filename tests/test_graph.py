"""Integration tests for the LangGraph pipeline."""

import json
from io import StringIO
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from apply_operator.state import ApplicationState, JobListing, ResumeData


class TestGraphCompilation:
    """Tests that the graph compiles and has expected structure."""

    def test_graph_compiles(self) -> None:
        from apply_operator.graph import build_graph

        graph = build_graph()
        assert graph is not None

    def test_graph_has_expected_nodes(self) -> None:
        from apply_operator.graph import build_graph

        graph = build_graph()
        node_names = set(graph.get_graph().nodes)
        expected = {
            "__start__",
            "__end__",
            "parse_resume",
            "search_jobs",
            "analyze_fit",
            "skip_job",
            "fill_application",
            "report_results",
        }
        assert expected == node_names


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
    """Create jobs for testing (fit_score starts at 0)."""
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
    """Mock parse_resume: return a canned resume."""
    return {"resume": _make_resume()}


def _fake_search(jobs: list[JobListing]):  # type: ignore[no-untyped-def]
    """Return a factory for a mock search_jobs that returns given jobs."""

    def _search(state: ApplicationState) -> dict[str, Any]:
        return {"jobs": jobs, "current_job_index": 0}

    return _search


def _fake_analyze(scores: list[float]):  # type: ignore[no-untyped-def]
    """Return a factory for a mock analyze_fit that assigns scores in order."""
    call_count = 0

    def _analyze(state: ApplicationState) -> dict[str, Any]:
        nonlocal call_count
        idx = state.current_job_index
        if idx >= len(state.jobs):
            return {}
        updated_jobs = list(state.jobs)
        updated_jobs[idx] = updated_jobs[idx].model_copy(update={"fit_score": scores[call_count]})
        call_count += 1
        return {"jobs": updated_jobs}

    return _analyze


def _noop_report(state: ApplicationState) -> dict[str, Any]:
    """Mock report_results: no-op."""
    return {}


class TestFullPipeline:
    """Integration tests that run the compiled graph with mocked external deps."""

    def _build_mocked_graph(
        self,
        jobs: list[JobListing],
        scores: list[float],
        mock_report: bool = True,
    ) -> Any:
        """Build graph with mocked parse, search, analyze, and optionally report."""
        patches = [
            patch("apply_operator.graph.parse_resume", _fake_parse),
            patch("apply_operator.graph.search_jobs", _fake_search(jobs)),
            patch("apply_operator.graph.analyze_fit", _fake_analyze(scores)),
        ]
        if mock_report:
            patches.append(patch("apply_operator.graph.report_results", _noop_report))

        from contextlib import ExitStack

        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            from apply_operator.graph import build_graph

            return build_graph()

    @pytest.mark.asyncio
    async def test_mixed_fit_scores(self) -> None:
        """Pipeline with a mix of high-fit and low-fit jobs."""
        jobs = _make_jobs(3)
        scores = [0.8, 0.3, 0.9]

        graph = self._build_mocked_graph(jobs, scores)
        result = await graph.ainvoke(
            ApplicationState(resume_path="test.pdf", job_urls=["https://example.com"])
        )

        assert result["total_applied"] == 2
        assert result["total_skipped"] == 1
        assert result["current_job_index"] == 3

        applied = [j for j in result["jobs"] if j.applied]
        skipped = [j for j in result["jobs"] if not j.applied]
        assert len(applied) == 2
        assert len(skipped) == 1

    @pytest.mark.asyncio
    async def test_no_jobs_found(self) -> None:
        """Pipeline terminates cleanly when no jobs are found."""
        graph = self._build_mocked_graph(jobs=[], scores=[])
        result = await graph.ainvoke(
            ApplicationState(resume_path="test.pdf", job_urls=["https://example.com"])
        )

        assert result["total_applied"] == 0
        assert result["total_skipped"] == 0

    @pytest.mark.asyncio
    async def test_all_low_fit(self) -> None:
        """All jobs skipped when all have low fit scores."""
        jobs = _make_jobs(3)
        scores = [0.2, 0.1, 0.4]

        graph = self._build_mocked_graph(jobs, scores)
        result = await graph.ainvoke(
            ApplicationState(resume_path="test.pdf", job_urls=["https://example.com"])
        )

        assert result["total_applied"] == 0
        assert result["total_skipped"] == 3
        assert all(not j.applied for j in result["jobs"])

    @pytest.mark.asyncio
    async def test_all_high_fit(self) -> None:
        """All jobs applied when all have high fit scores."""
        jobs = _make_jobs(2)
        scores = [0.85, 0.75]

        graph = self._build_mocked_graph(jobs, scores)
        result = await graph.ainvoke(
            ApplicationState(resume_path="test.pdf", job_urls=["https://example.com"])
        )

        assert result["total_applied"] == 2
        assert result["total_skipped"] == 0
        assert all(j.applied for j in result["jobs"])

    @pytest.mark.asyncio
    async def test_single_job_applied(self) -> None:
        """Single high-fit job is applied."""
        jobs = _make_jobs(1)
        scores = [0.7]

        graph = self._build_mocked_graph(jobs, scores)
        result = await graph.ainvoke(
            ApplicationState(resume_path="test.pdf", job_urls=["https://example.com"])
        )

        assert result["total_applied"] == 1
        assert result["total_skipped"] == 0
        assert result["jobs"][0].applied is True

    @pytest.mark.asyncio
    async def test_single_job_skipped(self) -> None:
        """Single low-fit job is skipped."""
        jobs = _make_jobs(1)
        scores = [0.3]

        graph = self._build_mocked_graph(jobs, scores)
        result = await graph.ainvoke(
            ApplicationState(resume_path="test.pdf", job_urls=["https://example.com"])
        )

        assert result["total_applied"] == 0
        assert result["total_skipped"] == 1
        assert result["jobs"][0].applied is False

    @pytest.mark.asyncio
    async def test_report_results_writes_json(self, tmp_path: Path) -> None:
        """report_results node writes results to JSON file."""
        jobs = _make_jobs(1)
        scores = [0.7]

        output_path = tmp_path / "results.json"

        # Build graph with real report_results but redirect output path
        graph = self._build_mocked_graph(jobs, scores, mock_report=False)

        with patch(
            "apply_operator.nodes.report_results.Path",
        ) as mock_path_cls:
            # Make Path("data/results.json") return our tmp path
            mock_path_obj = mock_path_cls.return_value
            mock_path_obj.parent.mkdir.return_value = None
            mock_path_obj.write_text.side_effect = lambda text: output_path.write_text(text)

            await graph.ainvoke(
                ApplicationState(resume_path="test.pdf", job_urls=["https://example.com"])
            )

        assert output_path.exists()
        data = json.loads(output_path.read_text())
        assert data["total_applied"] == 1
        assert len(data["jobs"]) == 1

    @pytest.mark.asyncio
    async def test_streaming_yields_all_node_names(self) -> None:
        """astream with updates mode yields events for every node in the pipeline."""
        jobs = _make_jobs(1)
        scores = [0.7]

        graph = self._build_mocked_graph(jobs, scores)
        initial = ApplicationState(resume_path="test.pdf", job_urls=["https://example.com"])

        node_names: list[str] = []
        async for event in graph.astream(initial, stream_mode="updates"):
            for name in event:
                node_names.append(name)

        # All pipeline nodes should appear (fill_application because score >= 0.6)
        assert "parse_resume" in node_names
        assert "search_jobs" in node_names
        assert "analyze_fit" in node_names
        assert "fill_application" in node_names
        assert "report_results" in node_names

    @pytest.mark.asyncio
    async def test_streaming_state_matches_ainvoke(self) -> None:
        """Accumulated streaming updates produce the same result as ainvoke."""
        jobs = _make_jobs(2)
        scores = [0.8, 0.4]

        # Build two separate graphs (mocks have internal state)
        graph1 = self._build_mocked_graph(jobs, scores)
        graph2 = self._build_mocked_graph(jobs, [0.8, 0.4])

        initial = ApplicationState(resume_path="test.pdf", job_urls=["https://example.com"])

        # Get result via ainvoke
        invoke_result = await graph1.ainvoke(initial)

        # Get result via streaming accumulation (same as _run_graph in main.py)
        stream_state: dict[str, Any] = {}
        async for event in graph2.astream(initial, stream_mode="updates"):
            for node_output in event.values():
                if node_output:
                    stream_state.update(node_output)

        # Key fields must match
        assert stream_state["total_applied"] == invoke_result["total_applied"]
        assert stream_state["total_skipped"] == invoke_result["total_skipped"]
        assert len(stream_state["jobs"]) == len(invoke_result["jobs"])
        for s_job, i_job in zip(stream_state["jobs"], invoke_result["jobs"], strict=True):
            assert s_job.applied == i_job.applied
            assert s_job.fit_score == i_job.fit_score


class TestPrintResults:
    """Tests for the _print_results CLI helper."""

    def test_prints_results_from_streamed_state(self) -> None:
        """_print_results works with dict state from streaming (not Pydantic objects)."""
        from apply_operator.main import _print_results

        state: dict[str, Any] = {
            "jobs": [
                JobListing(
                    url="https://example.com/1",
                    title="Python Dev",
                    company="Acme",
                    fit_score=0.8,
                    applied=True,
                ),
                JobListing(
                    url="https://example.com/2",
                    title="Go Dev",
                    company="Beta",
                    fit_score=0.3,
                    applied=False,
                ),
            ],
            "total_applied": 1,
            "total_skipped": 1,
        }

        # Should not raise
        from rich.console import Console

        test_console = Console(file=StringIO(), width=120)
        with patch("apply_operator.main.console", test_console):
            _print_results(state)

        output = test_console.file.getvalue()  # type: ignore[union-attr]
        assert "Python Dev" in output
        assert "Go Dev" in output
        assert "Applied" in output
        assert "Skipped" in output
