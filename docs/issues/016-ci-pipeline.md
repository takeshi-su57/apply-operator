# [Chore]: Set up CI pipeline with GitHub Actions

**Labels:** `priority:medium`
**Depends on:** [015](015-comprehensive-testing.md)

## Description

Set up GitHub Actions CI to run lint, type check, and tests on every push to main and on pull requests.

## Motivation

- Automated quality gates prevent regressions from being merged
- Standard practice for any non-trivial project
- CI badge in README signals project quality

## Proposed Solution

Three parallel jobs: lint, type-check, test.

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -e ".[dev]"
      - run: ruff check src/ tests/
      - run: ruff format --check src/ tests/

  type-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -e ".[dev]"
      - run: mypy src/

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -e ".[dev]"
      - run: playwright install chromium --with-deps
      - run: pytest --cov=apply_operator
```

## Alternatives Considered

- **GitLab CI** — GitHub Actions is standard for GitHub repos
- **Pre-commit hooks only** — local-only, doesn't catch issues on other machines

## Acceptance Criteria

- [ ] `.github/workflows/ci.yml` created
- [ ] All 3 jobs (lint, type-check, test) pass on a PR
- [ ] CI badge added to `README.md`
- [ ] `ruff check` and `mypy` pass

## Files Touched

- `.github/workflows/ci.yml` — create
- `README.md` — add CI badge

## Related Issues

- Blocked by [015](015-comprehensive-testing.md)
