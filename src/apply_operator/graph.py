"""LangGraph StateGraph assembly for the job application agent."""

from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from apply_operator.nodes.analyze_fit import analyze_fit
from apply_operator.nodes.fill_application import fill_application
from apply_operator.nodes.generate_cover_letter import generate_cover_letter
from apply_operator.nodes.parse_resume import parse_resume
from apply_operator.nodes.report_results import report_results
from apply_operator.nodes.search_jobs import search_jobs
from apply_operator.state import ApplicationState


def should_apply(state: ApplicationState) -> str:
    """Route based on fit score: apply or skip to next job.

    analyze_fit scores the job at current_job_index without advancing.
    This function checks that scored job and routes accordingly.
    """
    idx = state["current_job_index"]
    if idx >= len(state["jobs"]):
        return "report"

    current_job = state["jobs"][idx]
    if current_job.fit_score >= 0.6:
        return "apply"
    return "skip"


def has_more_jobs(state: ApplicationState) -> str:
    """Check if there are more jobs to process."""
    if state["current_job_index"] < len(state["jobs"]):
        return "next"
    return "done"


def skip_job(state: ApplicationState) -> dict[str, Any]:
    """Advance past a low-scoring job, incrementing the skip counter."""
    return {
        "current_job_index": state["current_job_index"] + 1,
        "total_skipped": state["total_skipped"] + 1,
    }


def build_graph(
    checkpointer: BaseCheckpointSaver | None = None,  # type: ignore[type-arg]
) -> CompiledStateGraph:  # type: ignore[type-arg]
    """Build and return the compiled job application agent graph.

    Args:
        checkpointer: Optional LangGraph checkpoint saver for state persistence.

    Flow:
        START -> parse_resume -> search_jobs -> analyze_fit
            -> [fit >= 0.6] -> generate_cover_letter -> fill_application -> (loop or report)
            -> [fit < 0.6] -> skip_job -> analyze_fit (loop)
            -> [no more jobs] -> report_results -> END
    """
    graph = StateGraph(ApplicationState)

    # Add nodes
    graph.add_node("parse_resume", parse_resume)
    graph.add_node("search_jobs", search_jobs)
    graph.add_node("analyze_fit", analyze_fit)
    graph.add_node("skip_job", skip_job)
    graph.add_node("generate_cover_letter", generate_cover_letter)
    graph.add_node("fill_application", fill_application)
    graph.add_node("report_results", report_results)

    # Linear flow: parse -> search -> first analysis
    graph.set_entry_point("parse_resume")
    graph.add_edge("parse_resume", "search_jobs")
    graph.add_edge("search_jobs", "analyze_fit")

    # Conditional: analyze_fit -> cover letter + apply, skip, or report
    graph.add_conditional_edges(
        "analyze_fit",
        should_apply,
        {
            "apply": "generate_cover_letter",
            "skip": "skip_job",
            "report": "report_results",
        },
    )

    # Cover letter flows into form filling
    graph.add_edge("generate_cover_letter", "fill_application")

    # skip_job advances index and loops back to analyze next job
    graph.add_edge("skip_job", "analyze_fit")

    # After application, loop back to analyze next job
    graph.add_conditional_edges(
        "fill_application",
        has_more_jobs,
        {
            "next": "analyze_fit",
            "done": "report_results",
        },
    )

    # Terminal
    graph.add_edge("report_results", END)

    return graph.compile(checkpointer=checkpointer)
