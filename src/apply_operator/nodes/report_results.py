"""Node: Generate final report of all application results."""

import json
from pathlib import Path

from apply_operator.state import ApplicationState


def report_results(state: ApplicationState) -> dict:
    """Save results to JSON and print summary.

    Writes application results to data/results.json for later review.
    """
    results = {
        "total_applied": state.total_applied,
        "total_skipped": state.total_skipped,
        "errors": state.errors,
        "jobs": [job.model_dump() for job in state.jobs],
    }

    output_path = Path("data/results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2))

    return {}
