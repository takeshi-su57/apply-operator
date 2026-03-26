# [Chore]: Project setup and verify toolchain

**Labels:** `priority:high`, `good first issue`
**Depends on:** None

## Description

Get the project installable and the CLI responding. Verify the entire Python toolchain (uv, ruff, mypy, pytest, Playwright) works before writing any application logic. Add OpenRouter as a supported LLM provider.

## Motivation

- The scaffold has stubs in place but nothing has been installed or verified
- Catching toolchain issues now prevents debugging them later during feature work
- Establishes the baseline: if setup works, all future issues can assume a working dev environment

## Tasks

- [x] Create a Python virtual environment (`.venv/`) using `uv venv`
- [x] Run `uv pip install -e ".[dev]"` — verify all dependencies install cleanly
- [x] Run `playwright install chromium` — verify browser binary downloads
- [x] Copy `.env.example` to `.env` and add a real LLM API key
- [x] Run `python -m apply_operator --help` — verify CLI loads and shows commands
- [x] Run `pytest` — verify the 2 existing stub tests pass
- [x] Run `ruff check src/ tests/` — verify no lint errors
- [x] Run `mypy src/` — verify no type errors (fix minor issues in stubs if needed)

## Acceptance Criteria

- [x] `python -m apply_operator --help` shows `run` and `parse-resume` commands
- [x] `pytest` passes with 2 green tests
- [x] `ruff check src/ tests/` reports no errors
- [x] `mypy src/` reports no errors
- [x] `.env` is configured with a working API key

## Changes Made

### Toolchain: pip → uv
- Migrated from `pip` to `uv` as the package manager (faster installs)
- Updated `CLAUDE.md`, `README.md`, `docs/guide/developer.md` to reflect uv commands

### New file: `src/apply_operator/__main__.py`
- Created to enable `python -m apply_operator` (was missing, caused startup error)

### OpenRouter support
- Added `openrouter` as a LLM provider option in `config.py`
- Added `OPENROUTER_API_KEY` and `OPENROUTER_BASE_URL` env vars
- Added OpenRouter case in `tools/llm_provider.py` (uses `ChatOpenAI` with custom base URL)
- Updated `.env.example`, `README.md`, `docs/guide/developer.md`

### mypy fixes (strict mode)
- All node functions: `-> dict` changed to `-> dict[str, Any]` (5 files)
- `graph.py`: return type changed to `CompiledStateGraph`
- `tools/llm_provider.py`: wrapped API keys with `SecretStr`, fixed `ChatAnthropic` kwargs
- `main.py`: replaced `dict` with `dict[str, Any]`, removed `# type: ignore`
- `pyproject.toml`: added mypy override for `fitz` (untyped module)

### ruff fixes
- `main.py`: removed empty f-string prefix
- `prompts/form_filling.py`: fixed line too long
- `pyproject.toml`: added B008 per-file ignore for `main.py` (Typer idiom)

### Docs realignment
- Updated roadmap and issues (005, 006, 009, 017) to reflect new architecture direction:
  no per-site credentials, session persistence, user intervention for login/CAPTCHA, real-user browsing with pagination

## Notes

Originally a verification-only issue, but required fixes to pass strict mypy and ruff checks. Also took the opportunity to add OpenRouter support, migrate to uv, and realign the issue roadmap.
