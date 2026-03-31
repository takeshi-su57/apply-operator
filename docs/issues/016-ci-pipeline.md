# [Chore]: Set up CI pipeline with GitHub Actions

**Labels:** `priority:medium`
**Depends on:** [015](015-comprehensive-testing.md)

## Description

Set up GitHub Actions CI to run lint, type check, and tests on every push to main and on pull requests.

## Motivation

- Automated quality gates prevent regressions from being merged
- Standard practice for any non-trivial project
- CI badge in README signals project quality

## Implementation

### Workflow: `.github/workflows/ci.yml`

Three parallel jobs using `uv` (via `astral-sh/setup-uv@v4`) for fast installs:

| Job | Steps |
|-----|-------|
| **lint** | `ruff check src/ tests/` + `ruff format --check src/ tests/` |
| **type-check** | `mypy src/` |
| **test** | `playwright install chromium --with-deps` + `pytest --cov=apply_operator` |

Triggers on push to `main` and all PRs targeting `main`. Uses `concurrency` to cancel in-progress runs when new commits are pushed.

### CI badge

Added to `README.md`:
```markdown
[![CI](https://github.com/takeshi-su57/apply-operator/actions/workflows/ci.yml/badge.svg)]
```

## Alternatives Considered

- **GitLab CI** -- GitHub Actions is standard for GitHub repos
- **Pre-commit hooks only** -- local-only, doesn't catch issues on other machines
- **pip instead of uv** -- uv is the project's package manager and significantly faster

## Acceptance Criteria

- [x] `.github/workflows/ci.yml` created
- [x] All 3 jobs (lint, type-check, test) defined
- [x] CI badge added to `README.md`
- [x] `ruff check` and `mypy` pass locally

## Files Touched

- `.github/workflows/ci.yml` -- **new**: CI workflow
- `README.md` -- added CI badge

## Related Issues

- Blocked by [015](015-comprehensive-testing.md)
