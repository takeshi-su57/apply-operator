# [Chore]: Achieve comprehensive test coverage

**Labels:** `priority:medium`
**Depends on:** [009](009-fill-application-node.md)

## Description

Fill test coverage gaps across all modules. Each prior issue added some tests; this issue audits coverage and fills the gaps to reach > 80% overall.

## Motivation

- Individual issues may skip edge cases — this is the dedicated quality pass
- Good coverage catches regressions as the codebase evolves
- Required before setting up CI (issue 016)

## Tasks

- [ ] Run coverage report: `pytest --cov=apply_operator --cov-report=html`
- [ ] Audit: identify untested code paths
- [ ] Add missing tests:
  - `tests/test_config.py` — Settings loading, defaults, env var parsing
  - `tests/test_state.py` — all Pydantic models, defaults, validation
  - `tests/test_graph.py` — full pipeline integration, conditional routing, loop termination, empty jobs
  - `tests/test_main.py` — CLI commands with mock graph, invalid file paths
- [ ] Expand existing tests with edge cases
- [ ] Verify all tests pass: `pytest -v`

### Coverage targets

| Module | Target |
|--------|--------|
| `tools/` | 90%+ |
| `nodes/` | 80%+ |
| `state.py` | 100% |
| `config.py` | 90%+ |
| `graph.py` | 80%+ |
| `main.py` | 70%+ |

## Acceptance Criteria

- [ ] `pytest --cov` shows overall coverage > 80%
- [ ] All test files exist and pass
- [ ] No untested error paths in nodes
- [ ] Graph routing logic fully tested (apply, skip, loop, empty)
- [ ] `ruff check` and `mypy` pass

## Files Touched

- `tests/test_config.py` — create
- `tests/test_state.py` — create
- `tests/test_graph.py` — create or expand
- `tests/test_main.py` — create
- All existing `tests/test_*.py` — expand edge cases
- `tests/conftest.py` — add shared fixtures

## Related Issues

- Blocked by [009](009-fill-application-node.md)
- Blocks [016](016-ci-pipeline.md)
