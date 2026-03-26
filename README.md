# apply-operator

AI agent that automates job applications. Provide a resume PDF and job site URLs — the agent parses your resume, searches for relevant jobs, analyzes fit, fills application forms, and auto-submits.

## Features

- Resume PDF parsing with structured data extraction (PyMuPDF + LLM)
- Automated job site browsing and listing discovery (Playwright)
- LLM-powered resume-to-job fit scoring
- Automated form filling and submission
- Configurable LLM provider (OpenAI, Anthropic, Google)
- CLI with progress monitoring (Typer + Rich)
- Results exported to JSON

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.12+ |
| Agent Framework | LangGraph (StateGraph) |
| LLM | LangChain (OpenAI / Anthropic / Google) |
| Browser Automation | Playwright (async) |
| PDF Parsing | PyMuPDF |
| CLI | Typer + Rich |
| Config | Pydantic Settings + python-dotenv |
| Linting | Ruff |
| Type Checking | mypy (strict) |
| Testing | pytest |

## Project Structure

```
src/apply_operator/
├── main.py              # CLI entry point
├── config.py            # Settings (env vars)
├── state.py             # ApplicationState model
├── graph.py             # LangGraph StateGraph
├── nodes/               # Pipeline steps
│   ├── parse_resume.py
│   ├── search_jobs.py
│   ├── analyze_fit.py
│   ├── fill_application.py
│   └── report_results.py
├── tools/               # I/O utilities
│   ├── pdf_parser.py
│   ├── browser.py
│   └── llm_provider.py
└── prompts/             # LLM prompt templates
tests/                   # Test suite
data/                    # Runtime output (git-ignored)
docs/                    # Architecture docs + ADRs
```

## Prerequisites

- Python 3.12+
- An LLM API key (OpenAI, Anthropic, or Google)

## Quick Start

```bash
# Clone and install
git clone <repo-url>
cd apply-operator
pip install -e ".[dev]"

# Install browser binaries
playwright install

# Configure environment
cp .env.example .env
# Edit .env — add your LLM API key

# Run the agent
python -m apply_operator run --resume resume.pdf --urls job_urls.txt
```

## Commands

| Command | Description |
|---------|-------------|
| `python -m apply_operator run` | Run full application pipeline |
| `python -m apply_operator parse-resume` | Parse resume only |
| `pytest` | Run tests |
| `ruff check src/ tests/` | Lint |
| `ruff format src/ tests/` | Format |
| `mypy src/` | Type check |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `openai` | LLM provider: `openai`, `anthropic`, `google` |
| `LLM_MODEL` | `gpt-4o` | Model name (provider-specific) |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `GOOGLE_API_KEY` | — | Google AI API key |
| `BROWSER_HEADLESS` | `true` | Run browser in headless mode |
| `LOG_LEVEL` | `INFO` | Logging level |

## AI Engineering

This project uses an AI engineering framework for structured development. See [AI_ENGINEERING.md](AI_ENGINEERING.md) for details.
