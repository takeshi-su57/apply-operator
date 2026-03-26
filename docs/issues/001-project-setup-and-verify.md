# [Chore]: Project setup and verify toolchain

**Labels:** `priority:high`, `good first issue`
**Depends on:** None

## Description

Get the project installable and the CLI responding. Verify the entire Python toolchain (pip, ruff, mypy, pytest, Playwright) works before writing any application logic.

## Motivation

- The scaffold has stubs in place but nothing has been installed or verified
- Catching toolchain issues now prevents debugging them later during feature work
- Establishes the baseline: if setup works, all future issues can assume a working dev environment

## Tasks

- [ ] Create a Python virtual environment (`.venv/`)
- [ ] Run `pip install -e ".[dev]"` — verify all dependencies install cleanly
- [ ] Run `playwright install chromium` — verify browser binary downloads
- [ ] Copy `.env.example` to `.env` and add a real LLM API key
- [ ] Run `python -m apply_operator --help` — verify CLI loads and shows commands
- [ ] Run `pytest` — verify the 2 existing stub tests pass
- [ ] Run `ruff check src/ tests/` — verify no lint errors
- [ ] Run `mypy src/` — verify no type errors (fix minor issues in stubs if needed)

## Acceptance Criteria

- [ ] `python -m apply_operator --help` shows `run` and `parse-resume` commands
- [ ] `pytest` passes with 2 green tests
- [ ] `ruff check src/ tests/` reports no errors
- [ ] `mypy src/` reports no errors (or known issues documented)
- [ ] `.env` is configured with a working API key

## Notes

No code changes expected — this is a verification issue. If mypy or ruff report errors in the existing stubs, fix them as part of this issue.
