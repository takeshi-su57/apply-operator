# Deployment Guide

How to package and deploy apply-operator.

## Current Deployment Model

apply-operator is a **single-user CLI tool** that runs locally. There is no server, container, or cloud deployment — the user runs it on their machine.

This guide covers packaging for distribution and potential future deployment patterns.

## Local Installation (End User)

### From source

```bash
git clone <repo-url>
cd apply-operator
pip install .
playwright install chromium

# Configure
cp .env.example .env
# Edit .env with API key

# Run
apply-operator run --resume resume.pdf --urls urls.txt
```

### From built wheel

```bash
pip install apply_operator-0.1.0-py3-none-any.whl
playwright install chromium
```

## Building a Distribution Package

### Build wheel + sdist

```bash
pip install build
python -m build
```

Output in `dist/`:
```
dist/
├── apply_operator-0.1.0-py3-none-any.whl
└── apply_operator-0.1.0.tar.gz
```

### Verify the build

```bash
pip install dist/apply_operator-0.1.0-py3-none-any.whl
apply-operator --help
```

## Docker (Optional)

For reproducible environments or future server deployment:

### Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system deps for Playwright
RUN apt-get update && apt-get install -y \
    libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libatspi2.0-0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml README.md ./
COPY src/ src/
RUN pip install --no-cache-dir .

# Install browser
RUN playwright install chromium

# Runtime
ENTRYPOINT ["apply-operator"]
```

### Build and run

```bash
docker build -t apply-operator .
docker run --rm \
    -v $(pwd)/data:/app/data \
    -v $(pwd)/resume.pdf:/app/resume.pdf \
    -v $(pwd)/urls.txt:/app/urls.txt \
    --env-file .env \
    apply-operator run --resume /app/resume.pdf --urls /app/urls.txt
```

**Note:** The Dockerfile is not included in the repo yet — create it when Docker deployment is needed.

## Environment Variables (Production)

Same variables as development. See the [Developer Guide](developer.md) for the full table.

For production use, ensure:
- `BROWSER_HEADLESS=true` (no display server available)
- `LOG_LEVEL=INFO` (not DEBUG — avoids logging sensitive resume data)
- API keys set via environment, not `.env` file

## Data Persistence

Results are written to `data/results.json` after each run. In Docker, mount the `data/` directory as a volume to persist results:

```bash
-v $(pwd)/data:/app/data
```

## Future Deployment Patterns

These are **not implemented** — documented here for planning purposes.

### Scheduled runs (cron)

```bash
# Run every morning at 8 AM
0 8 * * * cd /path/to/apply-operator && .venv/bin/apply-operator run \
    --resume /path/to/resume.pdf --urls /path/to/urls.txt
```

### Web API wrapper

If a web interface is added later, the agent could be wrapped with FastAPI:
- `POST /run` — trigger a job application run
- `GET /status` — check progress
- `GET /results` — fetch latest results

This would require adding: FastAPI, background task queue (e.g., Celery or asyncio tasks), and a database for multi-user support.

### Multi-user mode

The current architecture (local JSON storage, single `ApplicationState`) is designed for single-user. Multi-user would require:
- Database (PostgreSQL) instead of JSON files
- User authentication
- Job queue for concurrent runs
- LangGraph checkpointing with per-user thread IDs

## Release Checklist

Before releasing a new version:

1. Update version in `pyproject.toml`
2. Ensure all tests pass: `pytest`
3. Ensure lint + type check pass: `ruff check src/ tests/ && mypy src/`
4. Build: `python -m build`
5. Test the built wheel in a clean virtualenv
6. Tag the release: `git tag v0.1.0`
7. Push tag: `git push origin v0.1.0`
