"""Node: Generate final report of all application results."""

import json
import logging
from pathlib import Path
from typing import Any

from apply_operator.state import ApplicationState
from apply_operator.tools.logging_utils import log_node

logger = logging.getLogger(__name__)


@log_node
def report_results(state: ApplicationState) -> dict[str, Any]:
    """Save results to JSON and print summary.

    Writes application results to data/results.json for later review.
    """
    results = {
        "total_applied": state["total_applied"],
        "total_skipped": state["total_skipped"],
        "errors": state.get("errors", []),
        "jobs": [job.model_dump() for job in state["jobs"]],
    }

    output_path = Path("data/results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2))
    logger.info(
        "Results saved to %s | applied=%d skipped=%d errors=%d",
        output_path,
        state["total_applied"],
        state["total_skipped"],
        len(state.get("errors", [])),
    )

    return {}
