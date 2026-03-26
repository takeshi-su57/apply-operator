# Implementation Roadmap

Sequential issues for building the apply-operator agent. Each issue builds on the previous ones.

## Design Principles

- **No per-site credentials** — the agent detects login walls and prompts the user to log in manually
- **Session persistence** — cookies saved to `data/sessions/<domain>.json`, reused across runs
- **User intervention** — when CAPTCHA or bot detection occurs, the agent pauses for the user to handle it
- **Real-user browsing** — the agent navigates pages, clicks through listings, and handles pagination like a human would
- **LLM-assisted understanding** — the agent uses LLM to understand arbitrary page layouts, not hardcoded selectors

## Phase 1: Foundation (do these first, in order)

| # | Issue | Depends on | What you'll learn |
|---|-------|-----------|-------------------|
| [001](001-project-setup-and-verify.md) | Project Setup & Verify | — | Python toolchain, uv, editable installs, Typer CLI |
| [002](002-pdf-text-extraction.md) | PDF Text Extraction | 001 | PyMuPDF, first tool implementation |
| [003](003-llm-provider-setup.md) | LLM Provider Setup | 001 | LangChain, factory pattern, API keys, OpenRouter |
| [004](004-resume-structured-extraction.md) | Resume Structured Extraction | 002, 003 | **First LangGraph node**, LLM prompting, JSON parsing |
| [005](005-playwright-browser-basics.md) | Playwright + Session Persistence | 001 | Async browser automation, session save/load, user intervention |

## Phase 2: Core Pipeline (parallel tracks merge at 008)

| # | Issue | Depends on | What you'll learn |
|---|-------|-----------|-------------------|
| [006](006-search-jobs-node.md) | Search Jobs Node | 005 | Login detection, LLM-assisted scraping, pagination, real-user flow |
| [007](007-analyze-fit-node.md) | Analyze Fit Node | 003, 004 | Conditional routing, state updates |
| [008](008-minimal-graph-integration.md) | **Minimal Graph Integration** | 004, 006, 007 | **LangGraph wiring**, streaming, end-to-end flow |

## Phase 3: Full Agent (the hard part)

| # | Issue | Depends on | What you'll learn |
|---|-------|-----------|-------------------|
| [009](009-fill-application-node.md) | Fill Application Node | 005, 008 | Form automation, LLM-guided interaction, CAPTCHA handling |
| [010](010-cli-progress-and-reporting.md) | CLI Progress & Reporting | 008 | Rich Live display, graph streaming |

## Phase 4: Hardening

| # | Issue | Depends on | What you'll learn |
|---|-------|-----------|-------------------|
| [011](011-error-handling-and-retry.md) | Error Handling & Retry | 009 | Resilience patterns, exponential backoff |
| [012](012-langgraph-checkpointing.md) | LangGraph Checkpointing | 008 | Persistence, resume-on-crash |
| [013](013-state-model-refinement.md) | State Model Refinement | 008 | TypedDict, reducers, LangGraph internals |

## Phase 5: Polish

| # | Issue | Depends on | What you'll learn |
|---|-------|-----------|-------------------|
| [014](014-cover-letter-generation.md) | Cover Letter Generation | 007 | Adding nodes to existing graph |
| [015](015-comprehensive-testing.md) | Comprehensive Testing | 009 | Test strategy, coverage, mocking |
| [016](016-ci-pipeline.md) | CI Pipeline | 015 | GitHub Actions |
| [017](017-job-site-adapters.md) | Job Site Adapters | 009 | Adapter pattern, site-specific automation (no credentials) |

## Dependency Graph

```
001 Setup
 ├── 002 PDF Parser
 │    └── 004 Resume Node ──┐
 ├── 003 LLM Provider       │
 │    ├── 004 Resume Node    │
 │    └── 007 Fit Analysis ──┤
 └── 005 Browser + Sessions  │
      ├── 006 Job Search ────┤  (login detection, pagination, real-user flow)
      └─────────────────┐    │
                        │    │
                 008 Graph Integration ← MILESTONE: first working pipeline
                  │    │    │
                  │    009 Form Filling ← MILESTONE: full agent (+ CAPTCHA handling)
                  │    │
                  ├── 010 Progress UI
                  ├── 011 Error Handling
                  ├── 012 Checkpointing
                  ├── 013 State Refinement
                  ├── 014 Cover Letters
                  ├── 015 Full Testing
                  │    └── 016 CI
                  └── 017 Site Adapters (no credentials — uses shared sessions)
```

## Agent Browsing Flow

This is the core flow the agent follows for each job site URL:

```
1. Load saved session for domain (if exists)
2. Visit job site URL
3. Detect: logged in or login required?
   → Login required → Show browser, prompt user, save session after login
   → Already logged in → Continue
4. Find job listings on the page
5. For each job listing:
   a. Open the job details
   b. Analyze fit against resume (LLM)
   c. Fit good → Enter apply flow → Handle CAPTCHA if needed → Fill form → Submit
   d. Fit bad → Skip, go to next job
6. All jobs on current page processed?
   → Find pagination / "Load more" button
   → Exists → Click it, go back to step 4
   → None → Done with this site
7. Repeat for next job site URL
8. Report results
```

## How to Use These Issues

1. Start with **001** — get the project running
2. Work through Phase 1 in order (002 → 003 → 004 → 005)
3. Issues 002/003/005 can be done in parallel if you want
4. **Issue 008 is the first milestone** — you'll have a working pipeline
5. **Issue 009 is the second milestone** — full agent functionality
6. Phase 4-5 issues can be done in any order
