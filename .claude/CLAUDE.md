# apply-operator — Project Context

**Project name:** apply-operator

AI agent that automates job applications. User provides a resume PDF and job site URLs — the agent parses the resume, searches for jobs, analyzes fit, fills application forms, and auto-submits.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12+ |
| Agent Framework | LangGraph (StateGraph) |
| LLM | LangChain (OpenAI / Anthropic / Google — configurable) |
| Browser Automation | Playwright (async) |
| PDF Parsing | PyMuPDF (fitz) |
| CLI | Typer + Rich |
| Config | Pydantic Settings + python-dotenv |
| Package Manager | uv |
| Linting | Ruff |
| Type Checking | mypy (strict) |
| Testing | pytest + pytest-asyncio |
| Storage | Local JSON files |

## Repository Layout

```
src/apply_operator/        → Main Python package
  main.py                  → CLI entry point (Typer app)
  config.py                → Pydantic Settings (env var bindings)
  state.py                 → ApplicationState model (central data contract)
  graph.py                 → LangGraph StateGraph assembly
  nodes/                   → Graph node functions (one per file)
    parse_resume.py        → Extract + structure resume data
    search_jobs.py         → Browse job sites via Playwright
    analyze_fit.py         → LLM-based resume-to-job scoring
    fill_application.py    → Fill + submit forms via Playwright + LLM
    report_results.py      → Save results to JSON
  tools/                   → Utility modules (I/O, external services)
    pdf_parser.py          → PyMuPDF text extraction
    browser.py             → Playwright async context managers
    llm_provider.py        → LangChain model factory
  prompts/                 → LLM prompt templates as Python constants
tests/                     → pytest test suite
data/                      → Runtime data: results, cached resume (git-ignored)
docs/                      → Architecture docs, guides, ADRs
  architecture/            → System design + ADRs
  guide/                   → Developer and deployment guides
```

## Architecture Patterns

**LangGraph StateGraph** — The agent is a compiled StateGraph. `ApplicationState` (Pydantic model in `state.py`) flows through nodes. Each node is a function: `(state) -> dict` returning only the fields to update. LangGraph merges updates. See `.claude/rules/architecture.md`.

**Agent flow** — `parse_resume → search_jobs → [loop: analyze_fit → fill_application | skip] → report_results`

**Node design** — One public function per file in `nodes/`. Pure logic: receive state, call tools, return state delta. No global mutable state. Errors recorded in `state.errors`, pipeline continues.

**Tools layer** — Nodes call tools for I/O. `tools/llm_provider.py` returns a LangChain `BaseChatModel` based on `LLM_PROVIDER` env var. `tools/browser.py` provides async Playwright context managers. `tools/pdf_parser.py` wraps PyMuPDF.

**Prompts** — String templates in `prompts/` as Python constants with `{placeholder}` fields. One file per concern (resume analysis, job matching, form filling).

**Config** — All config via env vars loaded by Pydantic Settings (`config.py`). `.env` file supported via python-dotenv. See `.env.example` for all variables.

**Storage** — Local JSON files in `data/`. Results written after each run. No database.

**CLI** — Typer app in `main.py` with Rich for progress display. Commands: `run`, `parse-resume`.

## Key Commands

```bash
uv venv                    # Create virtual environment
uv pip install -e ".[dev]" # Install with dev dependencies
python -m apply_operator run --resume resume.pdf --urls urls.txt  # Run agent
python -m apply_operator parse-resume --resume resume.pdf         # Parse resume only
pytest                     # Run tests
ruff check src/ tests/     # Lint
ruff format src/ tests/    # Format
mypy src/                  # Type check
playwright install         # Install browser binaries
```

## Conventions

- **Commits:** Conventional commits — `type(scope): description`
- **File naming:** snake_case for files, PascalCase for classes
- **Typing:** strict mypy, all functions typed
- **Linting:** Ruff (line-length 100, Python 3.12 target)
- **Config:** Never hardcode API keys — use env vars via `config.py`

## Rules (Detailed Guidance)

- `.claude/rules/architecture.md` — LangGraph patterns, node design, tools layer, state, anti-patterns
- `.claude/rules/testing.md` — pytest strategy, mocking patterns, fixtures, coverage targets
- `.claude/rules/security.md` — API key management, .env handling, browser safety, personal data
- `.claude/rules/git-commit.md` — Conventional commit format, types, examples
- `.claude/rules/pull-request.md` — PR title format, description template, size guidelines
- `.claude/rules/gh-issue.md` — Issue title format, templates for bugs/features/chores
- `.claude/rules/ai-framework.md` — Sync protocol, skill/rule design, maintenance
- `.claude/rules/documentation.md` — Docs structure, ADR conventions

## Known Gaps

- Node implementations are stubs (TODO placeholders)
- No CI pipeline yet
- No LangGraph checkpointing configured yet (needed for resume on crash)
- Browser automation strategy for different job sites not designed yet
- No rate limiting or anti-bot detection handling
