# Architecture Overview

## System Design

apply-operator is a LangGraph-based AI agent that automates job applications.

```
                        ┌─────────────────────────────────┐
                        │          CLI (Typer + Rich)      │
                        └──────────────┬──────────────────┘
                                       │
                        ┌──────────────▼──────────────────┐
                        │     LangGraph StateGraph         │
                        │                                  │
                        │  parse_resume ──► search_jobs    │
                        │                      │           │
                        │              ┌───────▼────────┐  │
                        │              │  analyze_fit    │  │
                        │              └───┬────────┬───┘  │
                        │          skip ◄──┘        └──►   │
                        │          (next)     fill_application│
                        │              │              │     │
                        │              └──────┬───────┘     │
                        │                     │             │
                        │           report_results          │
                        └──────────────┬──────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                   │
              ┌─────▼─────┐    ┌──────▼──────┐    ┌──────▼──────┐
              │  PyMuPDF   │    │  Playwright  │    │  LangChain  │
              │ (PDF parse)│    │  (browser)   │    │  (LLM calls)│
              └────────────┘    └─────────────┘    └─────────────┘
```

## Agent Flow

1. **parse_resume** — Extract text from PDF, use LLM to structure it
2. **search_jobs** — Visit job site URLs, scrape job listings via Playwright
3. **analyze_fit** — LLM scores resume-to-job match (0.0-1.0)
4. **fill_application** — If fit >= 0.6, fill form fields via Playwright + LLM
5. **report_results** — Save results to JSON, print summary table

## Data Flow

All data flows through `ApplicationState` (Pydantic model). Each node receives the full state and returns a dict of fields to update. LangGraph handles state merging.

## Storage

Single-user, local JSON files in `data/`:
- `data/results.json` — Application results after each run
