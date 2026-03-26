# Architecture Rules

## Project Structure

apply-operator is a single Python package, not a monorepo. All source code lives in `src/apply_operator/`.

```
src/apply_operator/
├── main.py              # CLI entry point (Typer)
├── config.py            # Pydantic Settings
├── state.py             # ApplicationState — central data contract
├── graph.py             # LangGraph StateGraph assembly
├── nodes/               # Graph node functions
├── tools/               # I/O utilities (browser, PDF, LLM)
└── prompts/             # LLM prompt templates
```

## LangGraph StateGraph

The agent is built as a LangGraph `StateGraph` compiled into a runnable graph.

- **State**: `ApplicationState` in `state.py` — a Pydantic `BaseModel` that flows through all nodes
- **Nodes**: Functions registered via `graph.add_node("name", function)`
- **Edges**: Linear (`add_edge`) and conditional (`add_conditional_edges`) routing
- **Compilation**: `graph.compile()` returns a runnable that accepts initial state

### Agent Flow

```
START → parse_resume → search_jobs → analyze_fit
    → [fit >= 0.6] → fill_application → (next job) → analyze_fit
    → [fit < 0.6] → (next job) → analyze_fit
    → [no more jobs] → report_results → END
```

The loop over jobs is handled by conditional edges that check `current_job_index` against the jobs list length.

## Node Design Pattern

Each node is a module in `nodes/` with a single public function:

```python
# nodes/example_node.py
from apply_operator.state import ApplicationState

def example_node(state: ApplicationState) -> dict:
    """Node description."""
    # 1. Read from state
    # 2. Call tools (browser, LLM, etc.)
    # 3. Return ONLY the fields to update
    return {"field_name": new_value}
```

Rules:
- **One function per file** — the file name matches the function name
- **Return a dict** of state fields to update, not the full state. LangGraph handles merging.
- **No global mutable state** — all data flows through `ApplicationState`
- **Errors don't crash the pipeline** — catch exceptions, append to `state.errors`, continue
- **No direct I/O in nodes** — delegate to tools layer (`tools/`)

## Tools Layer

Tools are utility modules that handle external I/O. Nodes call tools; tools don't call nodes.

| Tool | File | Purpose |
|------|------|---------|
| PDF Parser | `tools/pdf_parser.py` | Extract text from PDF via PyMuPDF |
| Browser | `tools/browser.py` | Playwright async context managers |
| LLM Provider | `tools/llm_provider.py` | LangChain model factory (configurable provider) |

### LLM Provider

`get_llm()` returns a LangChain `BaseChatModel` based on the `LLM_PROVIDER` env var. Supports `openai`, `anthropic`, `google`. Provider-specific packages are imported lazily.

### Browser Tool

Playwright runs in async mode. Use the `get_page()` context manager:

```python
from apply_operator.tools.browser import get_page

async with get_page() as page:
    await page.goto(url)
    content = await page.content()
```

## Prompts

LLM prompt templates live in `prompts/` as Python string constants with `{placeholder}` fields:

```python
# prompts/resume_analysis.py
PARSE_RESUME = """Extract structured data from...
Resume text:
{resume_text}
Return ONLY valid JSON."""
```

Rules:
- One file per concern (resume analysis, job matching, form filling)
- Templates are constants, not functions
- Use `str.format()` or f-strings to fill placeholders
- Always request structured output (JSON) from the LLM

## State Model

`ApplicationState` in `state.py` is the single source of truth:

- **Inputs**: `resume_path`, `job_urls`
- **Parsed data**: `resume` (ResumeData)
- **Job pipeline**: `jobs` (list of JobListing), `current_job_index`
- **Tracking**: `total_applied`, `total_skipped`, `errors`

All sub-models (`ResumeData`, `JobListing`) are Pydantic `BaseModel` with typed fields and defaults.

## Configuration

`config.py` uses Pydantic Settings with `.env` file support:

```python
from apply_operator.config import get_settings
settings = get_settings()
```

All configuration comes from environment variables. Never hardcode values.

## Storage

Local JSON files in `data/` (git-ignored). `report_results` node writes `data/results.json` after each run. No database needed for single-user mode.

## Error Handling

- Nodes catch exceptions and record them: `state.errors.append(f"Node failed: {e}")`
- The pipeline continues to the next job on failure
- `report_results` includes all errors in the final output
- CLI displays errors in the results table

## Anti-Patterns (Do NOT)

- Put business logic in `main.py` — CLI is thin, delegates to graph
- Use global mutable state — all data flows through `ApplicationState`
- Make LLM calls directly in nodes — use `tools/llm_provider.py`
- Hardcode prompts in node functions — use `prompts/` templates
- Use synchronous Playwright calls — always use async API
- Store API keys in code — use env vars via `config.py`
- Return the full state from nodes — return only changed fields as a dict
- Create deeply nested class hierarchies — keep it flat (functions + Pydantic models)
- Add a database for single-user mode — JSON files are sufficient
- Import from one node into another — nodes are independent; share via state
