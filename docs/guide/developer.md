# Developer Guide

How to set up, develop, and test apply-operator locally.

## Prerequisites

| Requirement | Version | Check |
|-------------|---------|-------|
| Python | 3.12+ | `python --version` |
| uv | latest | `uv --version` |
| Git | any | `git --version` |
| LLM API key | — | At least one: OpenAI, Anthropic, Google, or OpenRouter |

## Initial Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd apply-operator
```

### 2. Create a virtual environment

```bash
uv venv

# Activate it:
# Linux/macOS
source .venv/bin/activate

# Windows (Git Bash)
source .venv/Scripts/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
# Install package with dev dependencies
uv pip install -e ".[dev]"

# Install Playwright browser binaries
playwright install chromium
```

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and add your LLM API key:

```bash
LLM_PROVIDER=openai        # or: anthropic, google, openrouter
LLM_MODEL=gpt-4o           # model name for your provider
OPENAI_API_KEY=sk-...       # your API key

# Or use OpenRouter for access to many models via one key:
# LLM_PROVIDER=openrouter
# LLM_MODEL=anthropic/claude-sonnet-4-20250514
# OPENROUTER_API_KEY=sk-or-v1-...
```

### 5. Verify the setup

```bash
# Check CLI loads
python -m apply_operator --help

# Run tests
pytest

# Lint + type check
ruff check src/ tests/
mypy src/
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLM_PROVIDER` | Yes | `openai` | LLM provider: `openai`, `anthropic`, `google`, `openrouter` |
| `LLM_MODEL` | Yes | `gpt-4o` | Model name (provider-specific) |
| `OPENAI_API_KEY` | If provider=openai | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | If provider=anthropic | — | Anthropic API key |
| `GOOGLE_API_KEY` | If provider=google | — | Google AI API key |
| `OPENROUTER_API_KEY` | If provider=openrouter | — | OpenRouter API key |
| `OPENROUTER_BASE_URL` | No | `https://openrouter.ai/api/v1` | OpenRouter API base URL |
| `BROWSER_HEADLESS` | No | `true` | `false` to see browser during development |
| `LOG_LEVEL` | No | `INFO` | `DEBUG` for verbose output |

## Project Structure

```
src/apply_operator/
├── main.py              # CLI entry point (Typer + Rich)
├── config.py            # Pydantic Settings — reads .env
├── state.py             # ApplicationState — central data model
├── graph.py             # LangGraph StateGraph wiring
├── nodes/               # Pipeline steps (one function per file)
│   ├── parse_resume.py  # PDF → structured resume data
│   ├── search_jobs.py   # Browse job sites → job listings
│   ├── analyze_fit.py   # LLM scores resume vs. job
│   ├── fill_application.py  # Playwright fills + submits forms
│   └── report_results.py    # Save JSON, print summary
├── tools/               # I/O utilities called by nodes
│   ├── pdf_parser.py    # PyMuPDF text extraction
│   ├── browser.py       # Playwright async context managers
│   └── llm_provider.py  # LangChain model factory
└── prompts/             # LLM prompt templates
    ├── resume_analysis.py
    ├── job_matching.py
    └── form_filling.py
tests/                   # pytest test suite
data/                    # Runtime output (git-ignored)
docs/                    # Architecture docs + ADRs
```

## Development Workflow

### Running the agent

```bash
# Full pipeline
python -m apply_operator run --resume resume.pdf --urls job_urls.txt

# Parse resume only (useful for testing)
python -m apply_operator parse-resume --resume resume.pdf
```

### Debugging with visible browser

Set `BROWSER_HEADLESS=false` in `.env` to watch Playwright interact with job sites:

```bash
BROWSER_HEADLESS=false python -m apply_operator run --resume resume.pdf --urls urls.txt
```

### Adding a new node

1. Create `src/apply_operator/nodes/<name>.py` with a single public function:
   ```python
   from apply_operator.state import ApplicationState

   def my_node(state: ApplicationState) -> dict[str, Any]:
       # ... logic ...
       return {"field": value}
   ```
2. Add to `src/apply_operator/nodes/__init__.py`
3. Wire into `src/apply_operator/graph.py` — add node + edges
4. Update `docs/architecture/architecture.md` — agent flow diagram

### Adding a new tool

1. Create `src/apply_operator/tools/<name>.py`
2. Import and use from node functions
3. Mock in tests — tools handle all external I/O

### Adding a new prompt template

1. Add constants to existing file in `prompts/` or create a new file
2. Use `{placeholder}` syntax for variable parts
3. Always request JSON output from the LLM

## All Commands

| Command | Description |
|---------|-------------|
| `python -m apply_operator run` | Run full pipeline |
| `python -m apply_operator parse-resume` | Parse resume only |
| `python -m apply_operator --help` | Show CLI help |
| `pytest` | Run all tests |
| `pytest -v` | Run tests (verbose) |
| `pytest -k test_name` | Run specific test |
| `ruff check src/ tests/` | Lint code |
| `ruff check --fix src/ tests/` | Auto-fix lint issues |
| `ruff format src/ tests/` | Format code |
| `mypy src/` | Type check |
| `playwright install chromium` | Install/update browser |

## Testing

Tests live in `tests/`. Shared fixtures are in `tests/conftest.py`.

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=apply_operator

# Run specific test file
pytest tests/test_pdf_parser.py
```

Key principle: **always mock external I/O** (LLM calls, browser, file system). See `.claude/rules/testing.md` for mocking patterns.

## Code Quality

All code must pass before committing:

```bash
ruff check src/ tests/     # No lint errors
ruff format src/ tests/    # Consistent formatting
mypy src/                  # No type errors
pytest                     # All tests pass
```

## Commit Conventions

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
feat: add cover letter generation node
fix: handle timeout in form submission
docs: add deployment guide
test: add tests for pdf parser
chore: update langchain dependency
```

See `.claude/rules/git-commit.md` for full details.

## Troubleshooting

### `playwright install` fails

Make sure you have system dependencies. On Linux:
```bash
playwright install-deps chromium
```

### Import errors after install

Make sure you installed in editable mode:
```bash
uv pip install -e ".[dev]"
```

### LLM calls fail

1. Check your API key is set in `.env`
2. Check `LLM_PROVIDER` matches the key you provided
3. Try `LOG_LEVEL=DEBUG` for detailed error output
