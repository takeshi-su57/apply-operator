# [Feature]: Implement fill_application node with browser form automation

**Labels:** `enhancement`, `priority:high`
**Depends on:** [005](005-playwright-browser-basics.md), [008](008-minimal-graph-integration.md)

## Description

Implement the real `fill_application` node that uses Playwright to navigate to a job application page, LLM to understand form fields, and Playwright again to fill and submit the form. This is the most complex node in the pipeline.

## Motivation

- This is the core value proposition — automating the tedious form-filling process
- Every job site has different forms, so we use LLM-guided field mapping instead of hardcoded selectors
- **This is the second milestone** — after this, the agent can actually apply to jobs

## Proposed Solution

**LLM-guided form filling approach:**
1. Navigate to application page
2. Extract form field metadata via JavaScript (`get_form_fields()`)
3. Send fields + resume data to LLM with `MAP_FORM_FIELDS` prompt
4. Parse LLM response (field_name → value mapping)
5. Fill each field with Playwright (text, dropdown, file upload, checkbox)
6. Submit and verify

### Form field extraction (JavaScript in browser)

```python
async def get_form_fields(page) -> list[dict]:
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

Some applications have Next → Next → Submit flows. Loop: extract fields → fill → click next → repeat until submit.

### File upload (resume PDF)

```python
file_input = await page.query_selector('input[type="file"]')
if file_input:
    await file_input.set_input_files(state.resume_path)
```

## Alternatives Considered

- **Hardcoded selectors per site** — fast for known sites but breaks when UI changes (deferred to [017](017-job-site-adapters.md))
- **Browser extension approach** — requires user to install extension; CLI-only is simpler

## Acceptance Criteria

- [ ] Node navigates to application page, fills form fields, and submits
- [ ] Works with at least one real job application form
- [ ] Text inputs, dropdowns, and file uploads handled
- [ ] Multi-page forms detected and handled
- [ ] Errors don't crash the pipeline — recorded in `job.error` and `state.errors`
- [ ] Tests pass with mocked Playwright page and LLM
- [ ] `ruff check` and `mypy` pass

## Files Touched

- `src/apply_operator/nodes/fill_application.py` — full implementation
- `src/apply_operator/tools/browser.py` — add `get_form_fields()`
- `src/apply_operator/prompts/form_filling.py` — refine `MAP_FORM_FIELDS`
- `tests/test_fill_application.py` — create

## Related Issues

- Blocked by [005](005-playwright-browser-basics.md) and [008](008-minimal-graph-integration.md)
- Blocks [011](011-error-handling-and-retry.md), [015](015-comprehensive-testing.md), [017](017-job-site-adapters.md)
