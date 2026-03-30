"""CLI entry point for the job application agent."""

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.live import Live
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from apply_operator.config import get_settings

logging.basicConfig(
    level=get_settings().log_level,
    format="%(name)s | %(message)s",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
)

app = typer.Typer(
    name="apply-operator",
    help="AI agent that automates job applications.",
)
console = Console()

BAR_WIDTH = 20


@app.command()
def run(
    resume: Path = typer.Option(..., "--resume", "-r", help="Path to resume PDF file"),
    urls: Path = typer.Option(
        ..., "--urls", "-u", help="Path to text file with job site URLs (one per line)"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed step output"),
) -> None:
    """Run the full job application pipeline."""
    if not resume.exists():
        console.print(f"[red]Resume file not found: {resume}[/red]")
        raise typer.Exit(code=1)

    if not urls.exists():
        console.print(f"[red]URLs file not found: {urls}[/red]")
        raise typer.Exit(code=1)

    job_urls = [line.strip() for line in urls.read_text().splitlines() if line.strip()]
    if not job_urls:
        console.print("[red]No URLs found in the file.[/red]")
        raise typer.Exit(code=1)

    console.print("[bold cyan]apply-operator[/bold cyan]")
    console.print(f"  Resume: {resume}")
    console.print(f"  Job URLs: {len(job_urls)} sites")
    console.print()

    from apply_operator.graph import build_graph
    from apply_operator.state import ApplicationState

    graph = build_graph()
    initial = ApplicationState(resume_path=str(resume), job_urls=job_urls)
    result, total_duration, step_times = asyncio.run(_run_graph(graph, initial, verbose))
    _print_results(result, total_duration, step_times, verbose)


def _build_status_panel(
    current_node: str,
    total_jobs: int,
    processed: int,
    applied: int,
    skipped: int,
    error_count: int,
    elapsed: float,
    step_times: dict[str, float],
    verbose: bool,
) -> Panel:
    """Build a Rich Panel showing live pipeline progress."""
    lines = Text()

    lines.append("Phase:    ", style="dim")
    lines.append(f"● {current_node}\n", style="bold cyan")

    lines.append("Jobs:     ", style="dim")
    lines.append(f"{processed} / {total_jobs}\n")

    lines.append("Applied:  ", style="dim")
    lines.append(f"{applied}", style="green")
    lines.append("   Skipped: ", style="dim")
    lines.append(f"{skipped}", style="yellow")
    lines.append("   Errors: ", style="dim")
    lines.append(f"{error_count}\n", style="red" if error_count > 0 else "dim")

    lines.append("Elapsed:  ", style="dim")
    lines.append(f"{elapsed:.1f}s\n")

    if verbose and step_times:
        lines.append("\nStep Timings:\n", style="bold")
        for step, duration in step_times.items():
            if step != "starting":
                lines.append(f"  {step}: ", style="cyan")
                lines.append(f"{duration:.2f}s\n")

    return Panel(lines, title="[bold]apply-operator[/bold]", border_style="cyan")


async def _run_graph(
    graph: Any,
    initial: Any,
    verbose: bool = False,
) -> tuple[dict[str, Any], float, dict[str, float]]:
    """Stream graph execution with a live Rich progress panel."""
    final_state: dict[str, Any] = {}
    current_node = "starting"
    total_jobs = 0
    processed = 0
    applied = 0
    skipped = 0
    error_count = 0
    step_times: dict[str, float] = {}
    pipeline_start = time.perf_counter()
    step_start = pipeline_start

    with Live(
        _build_status_panel(current_node, 0, 0, 0, 0, 0, 0.0, {}, verbose),
        console=console,
        refresh_per_second=4,
    ) as live:
        async for event in graph.astream(initial, stream_mode="updates"):
            now = time.perf_counter()

            for node_name, node_output in event.items():
                # Record timing for previous step
                step_duration = now - step_start
                step_times[current_node] = step_times.get(current_node, 0.0) + step_duration
                step_start = now
                current_node = node_name

                # Extract progress counters from node output
                if node_output:
                    final_state.update(node_output)
                    if "jobs" in node_output:
                        total_jobs = len(node_output["jobs"])
                    if "total_applied" in node_output:
                        applied = node_output["total_applied"]
                    if "total_skipped" in node_output:
                        skipped = node_output["total_skipped"]
                    if "current_job_index" in node_output:
                        processed = node_output["current_job_index"]
                    if "errors" in node_output:
                        error_count = len(node_output["errors"])

            elapsed = now - pipeline_start
            live.update(
                _build_status_panel(
                    current_node,
                    total_jobs,
                    processed,
                    applied,
                    skipped,
                    error_count,
                    elapsed,
                    step_times,
                    verbose,
                )
            )

    # Record final step timing
    final_now = time.perf_counter()
    step_times[current_node] = step_times.get(current_node, 0.0) + (final_now - step_start)
    total_duration = final_now - pipeline_start

    console.print()
    return final_state, total_duration, step_times


def _fit_score_bar(score: float) -> str:
    """Return a unicode bar string for a fit score (0.0-1.0)."""
    filled = int(score * BAR_WIDTH)
    if score >= 0.6:
        color = "green"
    elif score >= 0.4:
        color = "yellow"
    else:
        color = "red"
    bar = "█" * filled + "░" * (BAR_WIDTH - filled)
    return f"[{color}]{bar}[/{color}] {score:.0%}"


@app.command()
def parse_resume(
    resume: Path = typer.Option(..., "--resume", "-r", help="Path to resume PDF file"),
) -> None:
    """Parse a resume PDF and display extracted data."""
    if not resume.exists():
        console.print(f"[red]Resume file not found: {resume}[/red]")
        raise typer.Exit(code=1)

    from apply_operator.nodes.parse_resume import parse_resume as _parse_resume
    from apply_operator.state import ApplicationState

    state = ApplicationState(resume_path=str(resume))
    result = _parse_resume(state)
    resume_data = result.get("resume")

    if result.get("errors"):
        for err in result["errors"]:
            console.print(f"[yellow]{err}[/yellow]")

    if resume_data is None:
        console.print("[red]Failed to parse resume.[/red]")
        raise typer.Exit(code=1)

    table = Table(title="Resume Data")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Name", resume_data.name or "[dim]—[/dim]")
    table.add_row("Email", resume_data.email or "[dim]—[/dim]")
    table.add_row("Phone", resume_data.phone or "[dim]—[/dim]")
    table.add_row(
        "Skills",
        ", ".join(resume_data.skills) if resume_data.skills else "[dim]—[/dim]",
    )
    table.add_row("Summary", resume_data.summary or "[dim]—[/dim]")

    for i, exp in enumerate(resume_data.experience, 1):
        title = exp.get("title", "")
        company = exp.get("company", "")
        duration = exp.get("duration", "")
        description = exp.get("description") or ""
        sentences = [s for s in description.replace("•", ".").split(".") if s.strip()]
        header = f"[bold]{title}[/bold] @ {company} ({duration})"
        detail = f"{description}\n[dim]({len(sentences)} details)[/dim]" if description else ""
        table.add_row(f"Experience {i}", f"{header}\n{detail}" if detail else header)

    for edu in resume_data.education:
        degree = edu.get("degree", "")
        institution = edu.get("institution", "")
        year = edu.get("year", "")
        table.add_row("Education", f"{degree}, {institution} ({year})")

    console.print(table)


def _print_results(
    state: dict[str, Any],
    total_duration: float,
    step_times: dict[str, float],
    verbose: bool = False,
) -> None:
    """Print a summary table of application results."""
    table = Table(title="Application Results")
    table.add_column("Job Title", style="cyan")
    table.add_column("Company", style="magenta")
    table.add_column("Fit Score")
    table.add_column("Status")

    for job in state.get("jobs", []):
        title = job.title if hasattr(job, "title") else job.get("title", "Unknown")
        company = job.company if hasattr(job, "company") else job.get("company", "Unknown")
        fit_score = job.fit_score if hasattr(job, "fit_score") else job.get("fit_score", 0)
        applied = job.applied if hasattr(job, "applied") else job.get("applied", False)
        error = job.error if hasattr(job, "error") else job.get("error", "")

        if error:
            status = f"[red]Error: {error}[/red]"
        elif applied:
            status = "[green]Applied[/green]"
        else:
            status = "[yellow]Skipped[/yellow]"

        table.add_row(
            title or "Unknown",
            company or "Unknown",
            _fit_score_bar(fit_score),
            status,
        )

    console.print(table)
    console.print(f"\n[green]Total applied: {state.get('total_applied', 0)}[/green]")
    console.print(f"[yellow]Total skipped: {state.get('total_skipped', 0)}[/yellow]")
    console.print(f"\n[bold]Pipeline completed in {total_duration:.1f}s[/bold]")

    if verbose and step_times:
        console.print()
        timing_table = Table(title="Step Timings")
        timing_table.add_column("Step", style="cyan")
        timing_table.add_column("Duration", style="white")
        for step, duration in step_times.items():
            if step != "starting":
                timing_table.add_row(step, f"{duration:.2f}s")
        console.print(timing_table)


if __name__ == "__main__":
    app()
