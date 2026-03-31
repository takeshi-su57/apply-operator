"""Job site adapter registry.

Adapters handle site-specific quirks for popular job platforms.
The generic LLM approach is used as fallback when no adapter matches.
"""

from apply_operator.tools.adapters.base import JobSiteAdapter
from apply_operator.tools.adapters.indeed import IndeedAdapter
from apply_operator.tools.adapters.linkedin import LinkedInAdapter

_ADAPTERS: list[JobSiteAdapter] = [
    LinkedInAdapter(),
    IndeedAdapter(),
]


def get_adapter(url: str) -> JobSiteAdapter | None:
    """Return the adapter for a URL's domain, or None for generic fallback."""
    for adapter in _ADAPTERS:
        if adapter.matches(url):
            return adapter
    return None


__all__ = [
    "IndeedAdapter",
    "JobSiteAdapter",
    "LinkedInAdapter",
    "get_adapter",
]
