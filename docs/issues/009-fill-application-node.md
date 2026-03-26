# [Feature]: Implement fill_application node with browser form automation and CAPTCHA handling

**Labels:** `enhancement`, `priority:high`
**Depends on:** [005](005-playwright-browser-basics.md), [008](008-minimal-graph-integration.md)

## Description

Implement the real `fill_application` node that uses Playwright to navigate to a job application page, LLM to understand form fields, and Playwright again to fill and submit the form. When CAPTCHA or bot detection is encountered, the agent pauses for user intervention.

## Motivation

- This is the core value proposition — automating the tedious form-filling process
- Every job site has different forms, so we use LLM-guided field mapping instead of hardcoded selectors
- Bot detection during form submission is common — the agent must pause for user to solve CAPTCHAs
- **This is the second milestone** — after this, the agent can actually apply to jobs

## Proposed Solution

### LLM-guided form filling approach

1. Navigate to application page
2. Detect CAPTCHA or verification — if found, pause for user
3. Extract form field metadata via JavaScript (`get_form_fields()`)
4. Send fields + resume data to LLM with `MAP_FORM_FIELDS` prompt
5. Parse LLM response (field_name → value mapping)
6. Fill each field with Playwright (text, dropdown, file upload, checkbox)
7. Before submit — detect CAPTCHA again, pause if needed
8. Submit and verify

### CAPTCHA / bot detection

```python
async def detect_captcha(page: Page) -> bool:
    """Check if a CAPTCHA or bot verification is present."""
    captcha_selectors = [
        'iframe[src*="recaptcha"]', 'iframe[src*="hcaptcha"]',
        '[class*="captcha"]', '#captcha', '[data-captcha]',
        'iframe[src*="challenge"]',
    ]
    for selector in captcha_selectors:
        element = await page.query_selector(selector)
        if element and await element.is_visible():
            return True
    return False

async def handle_captcha_if_present(page: Page) -> None:
    """If CAPTCHA detected, pause for user to solve it."""
    if await detect_captcha(page):
        await wait_for_user(page, "CAPTCHA detected. Please solve it in the browser.")
```

### Form field extraction (JavaScript in browser)

```python
async def get_form_fields(page: Page) -> list[dict]:
    return await page.evaluate("""() => {
        const fields = [];
        document.querySelectorAll('input, select, textarea').forEach(el => {
            const label = document.querySelector(`label[for="${el.id}"]`)?.textContent
                || el.getAttribute('aria-label') || el.placeholder || el.name || '';
            fields.push({
                tag: el.tagName.toLowerCase(), type: el.type || 'text',
                name: el.name || el.id || '', label: label.trim(),
                required: el.required, selector: el.id ? '#' + el.id : `[name="${el.name}"]`,
                options: el.tagName === 'SELECT'
                    ? [...el.options].map(o => ({value: o.value, text: o.textContent})) : [],
            });
        });
        return fields;
    }""")
```

### Multi-page form handling

Some applications have Next → Next → Submit flows. Loop: extract fields → fill → click next → check for CAPTCHA → repeat until submit.

### File upload (resume PDF)

```python
file_input = await page.query_selector('input[type="file"]')
if file_input:
    await file_input.set_input_files(state.resume_path)
```

### Full node flow

```python
async def fill_application(state: ApplicationState) -> dict[str, Any]:
    job = state.jobs[state.current_job_index]
    errors = list(state.errors)

    try:
        async with get_page_with_session(job.url) as page:
            await page.goto(job.url, timeout=30000)

            # Handle CAPTCHA before filling
            await handle_captcha_if_present(page)

            # Multi-page form loop
            while True:
                fields = await get_form_fields(page)
                if not fields:
                    break

                # LLM maps resume data to form fields
                mapping = get_field_mapping(fields, state.resume)
                await fill_fields(page, mapping)

                # Check for next button vs submit
                next_btn = await page.query_selector('button:text("Next")')
                if next_btn:
                    await next_btn.click()
                    await page.wait_for_load_state("networkidle")
                    await handle_captcha_if_present(page)
                    continue

                # Handle CAPTCHA before submit
                await handle_captcha_if_present(page)

                submit_btn = await page.query_selector('button[type="submit"]')
                if submit_btn:
                    await submit_btn.click()
                    break

            job.applied = True
            return {
                "jobs": update_job(state.jobs, state.current_job_index, job),
                "current_job_index": state.current_job_index + 1,
                "total_applied": state.total_applied + 1,
            }
    except Exception as e:
        job.error = str(e)
        errors.append(f"Failed to apply to {job.title}: {e}")
        return {
            "jobs": update_job(state.jobs, state.current_job_index, job),
            "current_job_index": state.current_job_index + 1,
            "errors": errors,
        }
```

## Alternatives Considered

- **Hardcoded selectors per site** — fast for known sites but breaks when UI changes
- **Automated CAPTCHA solving** — unreliable and may violate site terms; user intervention is more robust
- **Browser extension approach** — requires user to install extension; CLI-only is simpler

## Acceptance Criteria

- [ ] Node navigates to application page, fills form fields, and submits
- [ ] CAPTCHA/bot detection pauses automation and prompts user
- [ ] User intervention resumes correctly after CAPTCHA is solved
- [ ] Works with at least one real job application form
- [ ] Text inputs, dropdowns, and file uploads handled
- [ ] Multi-page forms detected and handled
- [ ] Errors don't crash the pipeline — recorded in `job.error` and `state.errors`
- [ ] Tests pass with mocked Playwright page and LLM
- [ ] `ruff check` and `mypy` pass

## Files Touched

- `src/apply_operator/nodes/fill_application.py` — full implementation
- `src/apply_operator/tools/browser.py` — add `get_form_fields()`, `detect_captcha()`, `handle_captcha_if_present()`
- `src/apply_operator/prompts/form_filling.py` — refine `MAP_FORM_FIELDS`
- `tests/test_fill_application.py` — create

## Related Issues

- Blocked by [005](005-playwright-browser-basics.md) and [008](008-minimal-graph-integration.md)
- Blocks [011](011-error-handling-and-retry.md), [015](015-comprehensive-testing.md), [017](017-job-site-adapters.md)
