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

## Implementation

### Browser utilities added to `tools/browser.py`

**`FormField` TypedDict** — structured metadata for each form field:
- `tag`, `field_type`, `name`, `label`, `required`, `selector`, `options`

**`get_form_fields(page) -> list[FormField]`** — JavaScript evaluation that:
- Finds all `input`, `select`, `textarea` elements
- Skips `hidden`, `submit`, `button` types and elements without name/id
- Resolves labels via `label[for]`, parent `<label>`, `aria-label`, `placeholder`, `name`
- Builds CSS selector per field (`#id` or `[name="..."]`) using `CSS.escape()`
- Collects option value/text pairs for `<select>` elements

**`detect_captcha(page) -> bool`** — checks for CAPTCHA via:
- DOM selectors: `iframe[src*="recaptcha"]`, `iframe[src*="hcaptcha"]`, `.g-recaptcha`, `#captcha`, `[class*='captcha']`, `[data-captcha]`, `iframe[src*="challenge"]`
- Text indicators: "verify you are human", "are you a robot", "complete the captcha", "security check", "prove you're not a robot"

**`handle_captcha_if_present(page)`** — if CAPTCHA detected, calls `wait_for_user()` then `wait_for_page_ready()`

### Prompts in `prompts/form_filling.py`

**`MAP_FORM_FIELDS`** — enhanced with:
- `{job_title}`, `{company}`, `{summary}` placeholders for context-aware filling
- Field type instructions: checkboxes → `"true"/"false"`, file → `"RESUME_FILE"` sentinel, select → exact option text
- Uses field `name` as JSON key
- Cover letter instruction: compose brief answer using candidate summary + job context

**`DETECT_FORM_PAGE_TYPE`** (new) — classifies page as `"form"`, `"confirmation"`, `"error"`, or `"other"` for post-submit verification

### Node implementation in `nodes/fill_application.py`

Converted from sync stub to full async node following `search_jobs` pattern:

**Helper functions:**
- `_strip_markdown_json()` — strips markdown code fences from LLM responses
- `_format_experience()` / `_format_education()` — format resume data for prompt
- `_format_fields_for_prompt()` — format `FormField` list as readable text for LLM
- `_map_fields_with_llm(fields, resume, job)` — LLM-powered field-to-value mapping
- `_fill_field(page, field, value, resume_path)` — dispatches by field type:
  - text/email/tel/url/textarea → `page.fill()`
  - select → `page.select_option(label=value)`
  - checkbox/radio → `page.check()` / `page.uncheck()`
  - file → `page.set_input_files(resume_path)` when value is `"RESUME_FILE"`
- `_find_and_click(page, selectors)` — tries selectors in order, clicks first visible match
- `_verify_submission(page)` — text heuristic first, then LLM classification

**Main node flow:**
1. Open browser with `get_page_with_session(job.url)` (persistent session per domain)
2. Navigate to application URL, wait for page ready
3. Pre-form CAPTCHA check
4. Multi-page form loop (max 10 pages):
   - Extract form fields via `get_form_fields()`
   - LLM maps resume data to field values
   - Fill each field via `_fill_field()`
   - Pre-submit CAPTCHA check
   - Try "Next"/"Continue" button → continue loop
   - Try "Submit"/"Apply" button → break
   - Neither found → break (dead end)
5. Verify submission via `_verify_submission()`
6. Take evidence screenshot to `data/screenshots/`
7. Update job state accordingly
8. Error handling: outer try/except catches all, records in `job.error` and `state.errors`

### Test suite: `tests/test_fill_application.py`

26 tests across 7 test classes:
- `TestStripMarkdownJson` — code fence stripping
- `TestMapFieldsWithLlm` — JSON parsing, markdown handling, invalid responses
- `TestFillField` — text, dropdown, checkbox, file upload, error handling
- `TestFindAndClick` — visible match, no match, hidden elements
- `TestVerifySubmission` — heuristic detection, LLM detection, edge cases
- `TestFillApplication` — single page, multi-page, CAPTCHA, no fields, exceptions, file upload

## Alternatives Considered

- **Hardcoded selectors per site** — fast for known sites but breaks when UI changes
- **Automated CAPTCHA solving** — unreliable and may violate site terms; user intervention is more robust
- **Browser extension approach** — requires user to install extension; CLI-only is simpler

## Acceptance Criteria

- [x] Node navigates to application page, fills form fields, and submits
- [x] CAPTCHA/bot detection pauses automation and prompts user
- [x] User intervention resumes correctly after CAPTCHA is solved
- [ ] Works with at least one real job application form (requires manual E2E test)
- [x] Text inputs, dropdowns, and file uploads handled
- [x] Multi-page forms detected and handled
- [x] Errors don't crash the pipeline — recorded in `job.error` and `state.errors`
- [x] Tests pass with mocked Playwright page and LLM (26 tests)
- [x] `ruff check` and `mypy` pass

## Files Touched

- `src/apply_operator/nodes/fill_application.py` — full async implementation (363 lines)
- `src/apply_operator/tools/browser.py` — added `FormField`, `get_form_fields()`, `detect_captcha()`, `handle_captcha_if_present()` (366 lines total)
- `src/apply_operator/prompts/form_filling.py` — enhanced `MAP_FORM_FIELDS`, added `DETECT_FORM_PAGE_TYPE`
- `tests/test_fill_application.py` — 26 tests across 7 classes (692 lines)
- `tests/test_graph.py` — updated mock to use sync `_fake_fill` for graph compatibility

## Related Issues

- Blocked by [005](005-playwright-browser-basics.md) and [008](008-minimal-graph-integration.md)
- Blocks [011](011-error-handling-and-retry.md), [015](015-comprehensive-testing.md), [017](017-job-site-adapters.md)
