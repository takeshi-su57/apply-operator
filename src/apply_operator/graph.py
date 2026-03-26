"""LangGraph StateGraph assembly for the job application agent."""

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from apply_operator.nodes.analyze_fit import analyze_fit
from apply_operator.nodes.fill_application import fill_application
from apply_operator.nodes.parse_resume import parse_resume
from apply_operator.nodes.report_results import report_results
from apply_operator.nodes.search_jobs import search_jobs
from apply_operator.state import ApplicationState


def should_apply(state: ApplicationState) -> str:
    """Route based on fit score: apply or skip to next job."""
    if state.current_job_index >= len(state.jobs):
        return "report"

    current_job = state.jobs[state.current_job_index]
    if current_job.fit_score >= 0.6:
        return "apply"
    return "skip"


def has_more_jobs(state: ApplicationState) -> str:
    """Check if there are more jobs to process."""
    if state.current_job_index < len(state.jobs):
        return "next"
    return "done"


def build_graph() -> CompiledStateGraph:  # type: ignore[type-arg]
    """Build and return the compiled job application agent graph.

    Flow:
        START -> parse_resume -> search_jobs -> analyze_fit
            -> [fit >= 0.6] -> fill_application -> advance -> analyze_fit (loop)
            -> [fit < 0.6] -> advance -> analyze_fit (loop)
            -> [no more jobs] -> report_results -> END
    """
    graph = StateGraph(ApplicationState)

    # Add nodes
    graph.add_node("parse_resume", parse_resume)
    graph.add_node("search_jobs", search_jobs)
    graph.add_node("analyze_fit", analyze_fit)
    graph.add_node("fill_application", fill_application)
    graph.add_node("report_results", report_results)

    # Linear flow: parse -> search -> first analysis
    graph.set_entry_point("parse_resume")
    graph.add_edge("parse_resume", "search_jobs")
    graph.add_edge("search_jobs", "analyze_fit")

    # Conditional: analyze_fit -> apply or skip
    graph.add_conditional_edges(
        "analyze_fit",
        should_apply,
        {
            "apply": "fill_application",
            "skip": "analyze_fit",  # advance index and re-enter
            "report": "report_results",
        },
    )

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

    return graph.compile()
