"""CLI entry point for the job application agent."""

from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

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

    from apply_operator.tools.pdf_parser import extract_text

    text = extract_text(str(resume))
    if not text.strip():
        console.print("[yellow]No text content found in the PDF.[/yellow]")
        return

    console.print(f"[bold cyan]Extracted text[/bold cyan] ({len(text)} chars):\n")
    console.print(text)


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
