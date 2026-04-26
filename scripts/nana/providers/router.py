#!/usr/bin/env python3
"""Safe provider router for AXIS NANA Wave 2c.2.

Selects only the offline safe providers (none, mock).
No real LLM provider, no network, no credentials.
"""

from __future__ import annotations

from .base_provider import BaseProvider, ProviderResult
from .mock_provider import MockProvider
from .none_provider import NoneProvider

# Exhaustive registry — only safe offline providers allowed in this wave.
_SAFE_PROVIDERS: dict[str, BaseProvider] = {
    "none": NoneProvider(),
    "mock": MockProvider(),
}

DEFAULT_PROVIDER = "none"


def get_provider(name: str | None = None) -> BaseProvider:
    """Return the provider instance for *name*.

    Raises ValueError for any name not in the safe registry.
    """
    resolved = (name or DEFAULT_PROVIDER).strip().lower()
    if resolved not in _SAFE_PROVIDERS:
        allowed = ", ".join(sorted(_SAFE_PROVIDERS))
        raise ValueError(
            f"Provider '{resolved}' is not available in safe mode. "
            f"Allowed providers: {allowed}."
        )
    return _SAFE_PROVIDERS[resolved]


def route(
    execution: dict,
    provider_name: str | None = None,
    prompt_package: dict | None = None,
) -> ProviderResult:
    """Route *execution* to the requested safe provider and return its result.

    Args:
        execution: Execution payload dict (must include at least concept_id).
        provider_name: One of 'none' or 'mock'. Defaults to 'none'.
        prompt_package: Optional prompt package dict passed through to provider.

    Returns:
        ProviderResult from the selected provider.

    Raises:
        ValueError: If *provider_name* is not in the safe registry.
    """
    provider = get_provider(provider_name)
    return provider.run(
        execution=execution,
        prompt_package=prompt_package,
        enable_real_llm=False,  # hard-coded; never True in this wave
    )
