# [Feature]: Add real-time CLI progress display with Rich

**Labels:** `enhancement`, `priority:medium`
**Depends on:** [008](008-minimal-graph-integration.md)

## Description

Add real-time progress monitoring to the CLI using Rich. The user should see which step is running, how many jobs have been processed, and a live status panel — instead of waiting silently.

## Motivation

- A full pipeline run can take 10-30+ minutes
- Silent waiting is poor UX — users will think it's frozen
- LangGraph's `stream()` API provides per-node events that we can display

## Implementation

### Changes to `src/apply_operator/main.py`

- **Rich `Live` panel** (`_build_status_panel`): Replaces the old `✓ node_name` print with a real-time updating `Panel` showing:
  - Current node name (bold cyan)
  - Job progress: `processed / total`
  - Counters: applied (green), skipped (yellow), errors (red)
  - Elapsed time
  - (verbose) Per-step timing breakdown
- **`--verbose` / `-v` flag** on the `run` command: Adds per-step timing inside the live panel during execution, and a "Step Timings" table after completion
- **Per-step timing** via `time.perf_counter()`: Tracks cumulative duration per node, total pipeline duration
- **`_run_graph` rewrite**: Wraps `graph.astream()` in a `Live` context manager (4fps refresh), extracts counters from node outputs, returns `(state, total_duration, step_times)` tuple
- **Color-coded results table** (`_print_results`): Status column uses per-cell markup -- `[green]Applied`, `[yellow]Skipped`, `[red]Error: ...`
- **Fit score bars** (`_fit_score_bar`): Unicode `█░` blocks colored by threshold (green >= 0.6, yellow >= 0.4, red < 0.4) with percentage
- **Pipeline duration footer**: `Pipeline completed in X.Xs`

### Changes to `tests/test_graph.py`

- Updated `_print_results` call to match new 4-argument signature

### New file: `tests/test_main.py`

27 test cases covering:
- `TestBuildStatusPanel` (6 tests) -- panel rendering, counters, verbose/non-verbose, starting node exclusion
- `TestFitScoreBar` (9 tests) -- color thresholds, boundary values (0.0, 0.4, 0.6, 1.0), bar characters
- `TestPrintResults` (8 tests) -- color-coded status, duration display, verbose timing table, fit bars in table, empty jobs
- `TestRunGraph` (4 tests) -- state/duration/step_times return, counter extraction from events, verbose passthrough

## Alternatives Considered

- **Simple print statements** -- works but no dynamic updating
- **tqdm progress bar** -- designed for loops, not graph steps; Rich is more flexible

## Acceptance Criteria

- [x] User sees real-time progress during pipeline execution
- [x] Current step name and job progress visible
- [x] Results table color-coded: green (applied), yellow (skipped), red (error)
- [x] `--verbose` flag shows detailed step information
- [x] Total pipeline duration displayed at end
- [x] `ruff check` and `mypy` pass

## Files Touched

- `src/apply_operator/main.py` -- Rich Live panel, verbose flag, timing, color-coded results, fit score bars
- `tests/test_main.py` -- 27 new test cases
- `tests/test_graph.py` -- updated `_print_results` call signature

## Related Issues

- Blocked by [008](008-minimal-graph-integration.md)
