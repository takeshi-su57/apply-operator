# [Chore]: Achieve comprehensive test coverage

**Labels:** `priority:medium`
**Depends on:** [009](009-fill-application-node.md)

## Description

Audit test coverage across all modules and fill gaps to reach >80% overall. Prior issues added tests per-feature; this is the dedicated quality pass.

## Results

**Overall coverage: 81% -> 89% (256 tests, up from 202)**

### Coverage by module

| Module | Before | After | Target |
|--------|--------|-------|--------|
| `config.py` | 100% | 100% | 90%+ |
| `graph.py` | 100% | 100% | 80%+ |
| `logging_utils.py` | 78% | **100%** | 80%+ |
| `browser.py` | 79% | **96%** | 80%+ |
| `checkpoint.py` | 60% | **96%** | 80%+ |
| `state.py` | 98% | 98% | 100% |
| `nodes/` (all) | >90% | >90% | 80%+ |
| `llm_provider.py` | 89% | 89% | 90%+ |
| `main.py` | 50% | **64%** | 70%+ |
| **TOTAL** | **81%** | **89%** | >80% |

### What was added

**New test files (35 new tests):**
- `tests/test_config.py` (15 tests) -- Settings defaults, env var overrides, `.env` isolation
- `tests/test_state.py` (12 tests) -- ResumeData None coercion, JobListing defaults + cover_letter, TypedDict structure
- `tests/test_logging_utils.py` (8 tests) -- sync/async `@log_node` decorator: logging, timing, exception handling

**Expanded existing tests (19 new tests):**
- `tests/test_browser.py` (+8) -- `detect_captcha` (selector/text/false/exception), `handle_captcha_if_present`, `get_form_fields`
- `tests/test_checkpoint.py` (+5) -- `create_async_checkpointer`, `get_run_summaries` (completed/interrupted/unknown)
- `tests/test_main.py` (+6) -- CLI commands: missing files exit 1, empty URLs, empty runs, no checkpoint

**Infrastructure:**
- Added `pytest-cov>=7.0` to dev dependencies

### Known gap

`main.py` at 64% -- the uncovered lines are CLI command happy-path bodies (`asyncio.run` + checkpointer + graph streaming). The core helpers (`_run_graph`, `_print_results`, `_build_status_panel`) are 100% covered via dedicated tests in `test_main.py` and `test_graph.py`.

## Acceptance Criteria

- [x] `pytest --cov` shows overall coverage > 80% (89%)
- [x] All test files exist and pass (256 passed)
- [x] No untested error paths in nodes (all >90%)
- [x] Graph routing logic fully tested (100%)
- [x] `ruff check` and `mypy` pass

## Files Touched

- `tests/test_config.py` -- **new**
- `tests/test_state.py` -- **new**
- `tests/test_logging_utils.py` -- **new**
- `tests/test_browser.py` -- expanded (captcha, form fields)
- `tests/test_checkpoint.py` -- expanded (async checkpointer, run summaries)
- `tests/test_main.py` -- expanded (CLI commands)
- `pyproject.toml` -- added `pytest-cov` to dev deps

## Related Issues

- Blocked by [009](009-fill-application-node.md)
- Blocks [016](016-ci-pipeline.md)
