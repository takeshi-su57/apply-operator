# Security Rules

## API Keys

- LLM provider keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`) must come from environment variables
- Use `config.py` (Pydantic Settings) to access all configuration — never read `os.environ` directly
- `.env` is in `.gitignore` — never commit it
- `.env.example` documents all variables without real values — keep it updated

## Personal Data

- Resume data and application results are stored locally in `data/` (git-ignored)
- Never commit personal data (resumes, application results, credentials) to git
- Never log full resume text or personal details at INFO level — use DEBUG only
- The `data/` directory must be in `.gitignore`

## Browser Automation Safety

- Playwright runs headless by default (`BROWSER_HEADLESS=true`)
- User credentials for job sites (if needed) come from env vars, never hardcoded
- Screenshots taken during automation should be saved to `data/` (git-ignored)
- Be cautious with form submissions — the agent auto-submits, so form data must be accurate

## Logging

- Use Python `logging` module with the standard library
- Never log API keys, passwords, or tokens at any level
- Never log full resume text at INFO level
- Safe to log: job URLs, fit scores, application status, error messages

## What AI Must Never Generate

- Hardcoded API keys, tokens, passwords, or personal data
- `eval()`, `exec()`, or any dynamic code execution
- Code that bypasses rate limiting or anti-bot protections on job sites
- Disabled security checks or type checking (`# type: ignore` without justification)
- `subprocess.run` with `shell=True` and user-provided input
- Logging of sensitive data (API keys, resume PII at INFO level)
