# [Feature]: Add real-time CLI progress display with Rich

**Labels:** `enhancement`, `priority:medium`
**Depends on:** [008](008-minimal-graph-integration.md)

## Description

Add real-time progress monitoring to the CLI using Rich. The user should see which step is running, how many jobs have been processed, and a live status panel — instead of waiting silently.

## Motivation

- A full pipeline run can take 10-30+ minutes
- Silent waiting is poor UX — users will think it's frozen
- LangGraph's `stream()` API provides per-node events that we can display

## Proposed Solution

- Replace `graph.invoke()` with `graph.stream()` in `main.py`
- Use Rich `Live` display with a status panel showing: current node, job count, applied/skipped counts
- Add `--verbose` flag for detailed output (LLM prompts/responses, browser actions)
- Add timing information (total + per-step duration)
- Improve results table with color-coded status and fit score bars

### Key pattern (LangGraph streaming + Rich)

```python
from rich.live import Live
from rich.panel import Panel

with Live(console=console) as live:
    for event in graph.stream(initial_state):
        node_name = list(event.keys())[0]
        live.update(Panel(
            f"[cyan]{node_name}[/cyan]\nJobs: {processed}/{total}",
            title="apply-operator",
        ))
```

## Alternatives Considered

- **Simple print statements** — works but no dynamic updating
- **tqdm progress bar** — designed for loops, not graph steps; Rich is more flexible

## Acceptance Criteria

- [ ] User sees real-time progress during pipeline execution
- [ ] Current step name and job progress visible
- [ ] Results table color-coded: green (applied), yellow (skipped), red (error)
- [ ] `--verbose` flag shows detailed step information
- [ ] Total pipeline duration displayed at end
- [ ] `ruff check` and `mypy` pass

## Files Touched

- `src/apply_operator/main.py` — streaming + Rich Live display

## Related Issues

- Blocked by [008](008-minimal-graph-integration.md)
