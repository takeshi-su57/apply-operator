# Logging Rules

How to log consistently across nodes, tools, and LLM calls.

## Logger Setup

Every module uses its own logger:

```python
import logging

logger = logging.getLogger(__name__)
```

Never use `print()` for operational output — use `logger` or Rich console (CLI only).

## Log Levels

| Level | When to use | Examples |
|-------|-------------|---------|
| `DEBUG` | Internal mechanics, polling, retries | Page content stable at 5000 chars, networkidle timed out |
| `INFO` | Key pipeline milestones and results | Node entry/exit, LLM call start/finish, job scored, jobs found |
| `WARNING` | Recoverable issues, fallback used | Bad JSON from LLM (defaulting to 0), pagination element not found |
| `ERROR` | Failures that skip work | Node failed with exception, URL unreachable |

## LangGraph Node Logging

Every node must log entry and exit. Use the `log_node` decorator from `tools/logging_utils.py`:

```python
from apply_operator.tools.logging_utils import log_node

@log_node
def my_node(state: ApplicationState) -> dict[str, Any]:
    ...
```

The decorator automatically logs:
- `INFO` on entry: `node=my_node | started`
- `INFO` on exit: `node=my_node | completed | 2.35s`
- `ERROR` on exception: `node=my_node | failed | ValueError: ...`

Inside the node, log meaningful business events:
```python
logger.info("Fit score for %s (%s): %.2f", job.title, job.company, score)
```

## LLM Call Logging

Use the `purpose` parameter in `call_llm()` to describe what the call is for:

```python
response = call_llm(prompt, purpose="analyze_fit for Senior Engineer at TechCo")
```

The LLM provider logs:
- `INFO` on start: `LLM call | provider=openrouter model=gpt-4o purpose=analyze_fit for Senior Engineer at TechCo`
- `INFO` on finish: `LLM call | completed | 6.03s | ~1200 chars`

## Browser Action Logging

- `INFO`: Navigation (`goto`), login detection, session save
- `DEBUG`: Page ready checks, content stability polling
- `WARNING`: Page load timeouts, extraction failures

## Format Convention

Use pipe-delimited structured fields for machine-parseable logs:

```python
# Good — structured, scannable
logger.info("node=%s | started", node_name)
logger.info("LLM call | provider=%s model=%s purpose=%s", provider, model, purpose)
logger.info("Fit score for %s (%s): %.2f — %s", title, company, score, reasoning)

# Bad — unstructured prose
logger.info("Starting to process the node now")
logger.info("Called the LLM and got a response back")
```

## What NOT to Log

- API keys, tokens, or credentials at any level
- Full resume text or personal data at INFO (use DEBUG only)
- Full LLM prompts at INFO (use DEBUG)
- Full LLM responses at INFO (log summary: char count, parsed score, etc.)
- Redundant "about to call X" then "calling X" then "called X" — one start + one finish is enough

## Checklist for New Code

- [ ] Module has `logger = logging.getLogger(__name__)`
- [ ] Node function uses `@log_node` decorator
- [ ] LLM calls pass `purpose=` parameter
- [ ] Business events logged at INFO (scores, counts, decisions)
- [ ] Errors caught and logged before appending to `state.errors`
- [ ] No sensitive data in INFO-level logs
