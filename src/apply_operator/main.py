"""CLI entry point for the job application agent."""

import logging
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

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


@app.command()
def run(
    resume: Path = typer.Option(..., "--resume", "-r", help="Path to resume PDF file"),
    urls: Path = typer.Option(
        ..., "--urls", "-u", help="Path to text file with job site URLs (one per line)"
    ),
) -> None:
    """Run the full job application pipeline."""
    # Validate inputs
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

    # TODO: Build graph, create initial state, invoke
    # from apply_operator.graph import build_graph
    # from apply_operator.state import ApplicationState
    #
    # graph = build_graph()
    # state = ApplicationState(resume_path=str(resume), job_urls=job_urls)
    # result = graph.invoke(state)
    # _print_results(result)

    console.print("[yellow]Agent pipeline not yet implemented. Stubs are in place.[/yellow]")


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
    table.add_row("Skills", ", ".join(resume_data.skills) if resume_data.skills else "[dim]—[/dim]")
    table.add_row("Summary", resume_data.summary or "[dim]—[/dim]")

    for i, exp in enumerate(resume_data.experience, 1):
        title = exp.get("title", "")
        company = exp.get("company", "")
        duration = exp.get("duration", "")
        description = exp.get("description") or ""
        # Count sentences (split on . ! ?)
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


def _print_results(state: dict[str, Any]) -> None:
    """Print a summary table of application results."""
    table = Table(title="Application Results")
    table.add_column("Job Title", style="cyan")
    table.add_column("Company", style="magenta")
    table.add_column("Fit Score", style="green")
    table.add_column("Status", style="yellow")

    for job in state.get("jobs", []):
        status = "Applied" if job.get("applied") else "Skipped"
        error = job.get("error", "")
        if error:
            status = f"Error: {error}"
        table.add_row(
            job.get("title", "Unknown"),
            job.get("company", "Unknown"),
            f"{job.get('fit_score', 0):.0%}",
            status,
        )

    console.print(table)
    console.print(f"\n[green]Total applied: {state.get('total_applied', 0)}[/green]")
    console.print(f"[yellow]Total skipped: {state.get('total_skipped', 0)}[/yellow]")


if __name__ == "__main__":
    app()
