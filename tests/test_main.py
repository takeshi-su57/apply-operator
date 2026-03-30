"""Tests for CLI progress display and reporting (issue 010)."""

from io import StringIO
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from rich.console import Console
from rich.panel import Panel

from apply_operator.main import _build_status_panel, _fit_score_bar, _print_results, _run_graph
from apply_operator.state import JobListing


class TestBuildStatusPanel:
    """Tests for the live status panel builder."""

    def test_returns_panel(self) -> None:
        result = _build_status_panel(
            current_node="parse_resume",
            total_jobs=0,
            processed=0,
            applied=0,
            skipped=0,
            error_count=0,
            elapsed=0.0,
            step_times={},
            verbose=False,
        )
        assert isinstance(result, Panel)

    def test_panel_contains_node_name(self) -> None:
        panel = _build_status_panel(
            current_node="search_jobs",
            total_jobs=5,
            processed=2,
            applied=1,
            skipped=1,
            error_count=0,
            elapsed=10.5,
            step_times={},
            verbose=False,
        )
        # Render panel to string to check contents
        console = Console(file=StringIO(), width=80)
        console.print(panel)
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "search_jobs" in output
        assert "2 / 5" in output
        assert "10.5s" in output

    def test_panel_shows_counters(self) -> None:
        panel = _build_status_panel(
            current_node="fill_application",
            total_jobs=10,
            processed=7,
            applied=4,
            skipped=2,
            error_count=1,
            elapsed=30.0,
            step_times={},
            verbose=False,
        )
        console = Console(file=StringIO(), width=80)
        console.print(panel)
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "4" in output  # applied
        assert "2" in output  # skipped
        assert "1" in output  # errors

    def test_verbose_shows_step_times(self) -> None:
        panel = _build_status_panel(
            current_node="analyze_fit",
            total_jobs=3,
            processed=1,
            applied=0,
            skipped=0,
            error_count=0,
            elapsed=5.0,
            step_times={"parse_resume": 1.23, "search_jobs": 3.45},
            verbose=True,
        )
        console = Console(file=StringIO(), width=80)
        console.print(panel)
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "Step Timings" in output
        assert "parse_resume" in output
        assert "1.23s" in output
        assert "search_jobs" in output
        assert "3.45s" in output

    def test_non_verbose_hides_step_times(self) -> None:
        panel = _build_status_panel(
            current_node="analyze_fit",
            total_jobs=3,
            processed=1,
            applied=0,
            skipped=0,
            error_count=0,
            elapsed=5.0,
            step_times={"parse_resume": 1.23},
            verbose=False,
        )
        console = Console(file=StringIO(), width=80)
        console.print(panel)
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "Step Timings" not in output

    def test_starting_node_excluded_from_verbose_times(self) -> None:
        panel = _build_status_panel(
            current_node="parse_resume",
            total_jobs=0,
            processed=0,
            applied=0,
            skipped=0,
            error_count=0,
            elapsed=1.0,
            step_times={"starting": 0.5, "parse_resume": 0.5},
            verbose=True,
        )
        console = Console(file=StringIO(), width=80)
        console.print(panel)
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "starting" not in output
        assert "parse_resume" in output


class TestFitScoreBar:
    """Tests for the unicode fit score bar."""

    def test_high_score_green(self) -> None:
        bar = _fit_score_bar(0.8)
        assert "[green]" in bar
        assert "80%" in bar

    def test_medium_score_yellow(self) -> None:
        bar = _fit_score_bar(0.5)
        assert "[yellow]" in bar
        assert "50%" in bar

    def test_low_score_red(self) -> None:
        bar = _fit_score_bar(0.2)
        assert "[red]" in bar
        assert "20%" in bar

    def test_zero_score(self) -> None:
        bar = _fit_score_bar(0.0)
        assert "[red]" in bar
        assert "0%" in bar

    def test_perfect_score(self) -> None:
        bar = _fit_score_bar(1.0)
        assert "[green]" in bar
        assert "100%" in bar

    def test_bar_contains_block_characters(self) -> None:
        bar = _fit_score_bar(0.5)
        assert "\u2588" in bar  # filled block
        assert "\u2591" in bar  # empty block

    def test_threshold_boundary_060(self) -> None:
        bar = _fit_score_bar(0.6)
        assert "[green]" in bar

    def test_threshold_boundary_040(self) -> None:
        bar = _fit_score_bar(0.4)
        assert "[yellow]" in bar

    def test_just_below_040(self) -> None:
        bar = _fit_score_bar(0.39)
        assert "[red]" in bar


class TestPrintResults:
    """Tests for the enhanced results display."""

    def _capture_output(
        self,
        state: dict[str, Any],
        total_duration: float = 5.0,
        step_times: dict[str, float] | None = None,
        verbose: bool = False,
    ) -> str:
        test_console = Console(file=StringIO(), width=120)
        with patch("apply_operator.main.console", test_console):
            _print_results(state, total_duration, step_times or {}, verbose)
        return test_console.file.getvalue()  # type: ignore[union-attr]

    def test_color_coded_applied(self) -> None:
        state: dict[str, Any] = {
            "jobs": [
                JobListing(
                    url="https://example.com/1",
                    title="Python Dev",
                    company="Acme",
                    fit_score=0.8,
                    applied=True,
                ),
            ],
            "total_applied": 1,
            "total_skipped": 0,
        }
        output = self._capture_output(state)
        assert "Applied" in output
        assert "Python Dev" in output

    def test_color_coded_skipped(self) -> None:
        state: dict[str, Any] = {
            "jobs": [
                JobListing(
                    url="https://example.com/1",
                    title="Go Dev",
                    company="Beta",
                    fit_score=0.3,
                    applied=False,
                ),
            ],
            "total_applied": 0,
            "total_skipped": 1,
        }
        output = self._capture_output(state)
        assert "Skipped" in output

    def test_color_coded_error(self) -> None:
        state: dict[str, Any] = {
            "jobs": [
                JobListing(
                    url="https://example.com/1",
                    title="Java Dev",
                    company="Gamma",
                    fit_score=0.7,
                    applied=False,
                    error="Form submission failed",
                ),
            ],
            "total_applied": 0,
            "total_skipped": 0,
        }
        output = self._capture_output(state)
        assert "Error" in output
        assert "Form submission failed" in output

    def test_shows_pipeline_duration(self) -> None:
        state: dict[str, Any] = {"jobs": [], "total_applied": 0, "total_skipped": 0}
        output = self._capture_output(state, total_duration=42.3)
        assert "42.3s" in output

    def test_verbose_shows_step_timings_table(self) -> None:
        state: dict[str, Any] = {"jobs": [], "total_applied": 0, "total_skipped": 0}
        step_times = {"parse_resume": 1.5, "search_jobs": 3.2}
        output = self._capture_output(state, step_times=step_times, verbose=True)
        assert "Step Timings" in output
        assert "parse_resume" in output
        assert "1.50s" in output

    def test_non_verbose_hides_step_timings(self) -> None:
        state: dict[str, Any] = {"jobs": [], "total_applied": 0, "total_skipped": 0}
        step_times = {"parse_resume": 1.5}
        output = self._capture_output(state, step_times=step_times, verbose=False)
        assert "Step Timings" not in output

    def test_fit_score_bar_in_table(self) -> None:
        state: dict[str, Any] = {
            "jobs": [
                JobListing(
                    url="https://example.com/1",
                    title="Dev",
                    company="Co",
                    fit_score=0.75,
                    applied=True,
                ),
            ],
            "total_applied": 1,
            "total_skipped": 0,
        }
        output = self._capture_output(state)
        assert "75%" in output

    def test_empty_jobs(self) -> None:
        state: dict[str, Any] = {"jobs": [], "total_applied": 0, "total_skipped": 0}
        output = self._capture_output(state)
        assert "Application Results" in output
        assert "Total applied: 0" in output


class TestRunGraph:
    """Tests for the streaming graph execution with Live display."""

    @pytest.mark.asyncio
    async def test_returns_state_duration_and_step_times(self) -> None:
        """_run_graph returns a tuple of (state, duration, step_times)."""
        mock_graph = AsyncMock()
        mock_graph.astream = lambda *a, **kw: _async_iter([
            {"parse_resume": {"resume": "data"}},
            {"search_jobs": {"jobs": [], "current_job_index": 0}},
            {"report_results": {}},
        ])

        test_console = Console(file=StringIO(), width=80)
        with patch("apply_operator.main.console", test_console):
            result, duration, step_times = await _run_graph(mock_graph, {})

        assert isinstance(result, dict)
        assert isinstance(duration, float)
        assert duration > 0
        assert isinstance(step_times, dict)

    @pytest.mark.asyncio
    async def test_extracts_counters_from_events(self) -> None:
        """Progress counters are extracted from node outputs."""
        mock_graph = AsyncMock()
        mock_graph.astream = lambda *a, **kw: _async_iter([
            {"parse_resume": {"resume": "data"}},
            {"search_jobs": {"jobs": [1, 2, 3], "current_job_index": 0}},
            {"analyze_fit": {"jobs": [1, 2, 3]}},
            {"fill_application": {
                "jobs": [1, 2, 3],
                "current_job_index": 1,
                "total_applied": 1,
            }},
            {"report_results": {}},
        ])

        test_console = Console(file=StringIO(), width=80)
        with patch("apply_operator.main.console", test_console):
            result, _, _ = await _run_graph(mock_graph, {})

        assert result["total_applied"] == 1
        assert result["current_job_index"] == 1
        assert len(result["jobs"]) == 3

    @pytest.mark.asyncio
    async def test_step_times_populated(self) -> None:
        """Each node gets a timing entry in step_times."""
        mock_graph = AsyncMock()
        mock_graph.astream = lambda *a, **kw: _async_iter([
            {"parse_resume": {"resume": "data"}},
            {"search_jobs": {"jobs": []}},
            {"report_results": {}},
        ])

        test_console = Console(file=StringIO(), width=80)
        with patch("apply_operator.main.console", test_console):
            _, _, step_times = await _run_graph(mock_graph, {})

        assert "parse_resume" in step_times
        assert "search_jobs" in step_times
        assert "report_results" in step_times

    @pytest.mark.asyncio
    async def test_verbose_flag_passed_through(self) -> None:
        """Verbose mode does not crash."""
        mock_graph = AsyncMock()
        mock_graph.astream = lambda *a, **kw: _async_iter([
            {"parse_resume": {"resume": "data"}},
            {"report_results": {}},
        ])

        test_console = Console(file=StringIO(), width=80)
        with patch("apply_operator.main.console", test_console):
            result, _, _ = await _run_graph(mock_graph, {}, verbose=True)

        assert isinstance(result, dict)


async def _async_iter(items: list[Any]) -> Any:
    """Helper to create an async iterator from a list."""
    for item in items:
        yield item
