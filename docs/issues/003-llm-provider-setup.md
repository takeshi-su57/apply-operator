# [Feature]: Implement configurable LLM provider factory

**Labels:** `enhancement`, `priority:high`
**Depends on:** [001](001-project-setup-and-verify.md)

## Description

Implement the LLM provider factory in `tools/llm_provider.py` so the agent can call any supported LLM (OpenAI, Anthropic, Google) based on configuration. This is the foundation for all LLM-powered nodes.

## Motivation

- Every node that uses AI (resume parsing, fit analysis, form filling) needs an LLM client
- Users should be able to choose their provider without code changes
- A factory pattern keeps provider-specific imports isolated from node code

## Proposed Solution

- Implement `get_llm() -> BaseChatModel` that reads `LLM_PROVIDER` from config
- Lazy-import provider-specific LangChain classes (ChatOpenAI, ChatAnthropic, ChatGoogleGenerativeAI)
- Add `call_llm(prompt: str) -> str` convenience wrapper that handles `AIMessage` extraction
- Temperature fixed at `0.3` for deterministic output

### Key concepts (LangChain basics)

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
response = llm.invoke("Say hello")  # returns AIMessage
print(response.content)              # "Hello!"
```

## Alternatives Considered

- **LiteLLM** — unified LLM proxy, but adds another dependency; LangChain already abstracts providers
- **Direct API calls** — no abstraction, harder to switch providers

## Acceptance Criteria

- [ ] `get_llm()` returns correct type for `openai`, `anthropic`, `google` providers
- [ ] `ValueError` raised for unknown provider
- [ ] `call_llm("Say hello")` returns a non-empty string with a real API key
- [ ] Missing API key gives a clear error message
- [ ] Tests pass with mocked providers
- [ ] `ruff check` and `mypy` pass

## Files Touched

- `src/apply_operator/tools/llm_provider.py` — implement
- `tests/test_llm_provider.py` — create

## Related Issues

- Blocks [004](004-resume-structured-extraction.md), [006](006-search-jobs-node.md), [007](007-analyze-fit-node.md), [009](009-fill-application-node.md)
