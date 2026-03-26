# Implementation Roadmap

Sequential issues for building the apply-operator agent. Each issue builds on the previous ones.

## Phase 1: Foundation (do these first, in order)

| # | Issue | Depends on | What you'll learn |
|---|-------|-----------|-------------------|
| [001](001-project-setup-and-verify.md) | Project Setup & Verify | — | Python toolchain, editable installs, Typer CLI |
| [002](002-pdf-text-extraction.md) | PDF Text Extraction | 001 | PyMuPDF, first tool implementation |
| [003](003-llm-provider-setup.md) | LLM Provider Setup | 001 | LangChain, factory pattern, API keys |
| [004](004-resume-structured-extraction.md) | Resume Structured Extraction | 002, 003 | **First LangGraph node**, LLM prompting, JSON parsing |
| [005](005-playwright-browser-basics.md) | Playwright Browser Basics | 001 | Async programming, browser automation |

## Phase 2: Core Pipeline (parallel tracks merge at 008)

| # | Issue | Depends on | What you'll learn |
|---|-------|-----------|-------------------|
| [006](006-search-jobs-node.md) | Search Jobs Node | 005 | LLM-assisted scraping, async nodes |
| [007](007-analyze-fit-node.md) | Analyze Fit Node | 003, 004 | Conditional routing, state updates |
| [008](008-minimal-graph-integration.md) | **Minimal Graph Integration** | 004, 006, 007 | **LangGraph wiring**, streaming, end-to-end flow |

## Phase 3: Full Agent (the hard part)

| # | Issue | Depends on | What you'll learn |
|---|-------|-----------|-------------------|
| [009](009-fill-application-node.md) | Fill Application Node | 005, 008 | Form automation, LLM-guided interaction |
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
| [017](017-job-site-adapters.md) | Job Site Adapters | 009 | Adapter pattern, site-specific automation |

## Dependency Graph

```
001 Setup
 ├── 002 PDF Parser
 │    └── 004 Resume Node ──┐
 ├── 003 LLM Provider       │
 │    ├── 004 Resume Node    │
 │    └── 007 Fit Analysis ──┤
 └── 005 Playwright          │
      ├── 006 Job Search ────┤
      └─────────────────┐    │
                        │    │
                 008 Graph Integration ← MILESTONE: first working pipeline
                  │    │    │
                  │    009 Form Filling ← MILESTONE: full agent
                  │    │
                  ├── 010 Progress UI
                  ├── 011 Error Handling
                  ├── 012 Checkpointing
                  ├── 013 State Refinement
                  ├── 014 Cover Letters
                  ├── 015 Full Testing
                  │    └── 016 CI
                  └── 017 Site Adapters
```

## How to Use These Issues

1. Start with **001** — get the project running
2. Work through Phase 1 in order (002 → 003 → 004 → 005)
3. Issues 002/003/005 can be done in parallel if you want
4. **Issue 008 is the first milestone** — you'll have a working pipeline
5. **Issue 009 is the second milestone** — full agent functionality
6. Phase 4-5 issues can be done in any order
