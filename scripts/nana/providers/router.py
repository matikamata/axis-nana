#!/usr/bin/env python3
"""Safe provider router for AXIS NANA — Wave 2c.3.

Wave 2c.2: offline-only safe registry (none, mock).
Wave 2c.3: adds _REAL_PROVIDERS with gemini_vertex; gated behind allow_real flag.

DEFAULT_PROVIDER remains 'none'.
Real providers are never reachable by default.
"""

from __future__ import annotations

from .base_provider import BaseProvider, ProviderResult
from .gemini_vertex_provider import GeminiVertexProvider
from .mock_provider import MockProvider
from .none_provider import NoneProvider

# ---------------------------------------------------------------------------
# Safe offline providers — always available, no credentials, no network.
# ---------------------------------------------------------------------------
_SAFE_PROVIDERS: dict[str, BaseProvider] = {
    "none": NoneProvider(),
    "mock": MockProvider(),
}

# ---------------------------------------------------------------------------
# Real providers — only reachable when allow_real=True is explicitly passed.
# In Wave 2c.3 the adapter is present but the wave-level constant inside it
# (REAL_CALLS_ENABLED_IN_THIS_WAVE = False) prevents any actual API call.
# ---------------------------------------------------------------------------
_REAL_PROVIDERS: dict[str, BaseProvider] = {
    "gemini_vertex": GeminiVertexProvider(),
}

DEFAULT_PROVIDER = "none"


def get_provider(
    name: str | None = None,
    allow_real: bool = False,
) -> BaseProvider:
    """Return the provider instance for *name*.

    Args:
        name: Provider name. Defaults to DEFAULT_PROVIDER ('none').
        allow_real: If False (default), real providers raise ValueError.
                    If True, real providers are accessible but remain
                    internally gated by REAL_CALLS_ENABLED_IN_THIS_WAVE.

    Raises:
        ValueError: If *name* is unknown, or if *name* is a real provider
                    and *allow_real* is False.
    """
    resolved = (name or DEFAULT_PROVIDER).strip().lower()

    if resolved in _SAFE_PROVIDERS:
        return _SAFE_PROVIDERS[resolved]

    if resolved in _REAL_PROVIDERS:
        if not allow_real:
            safe_names = ", ".join(sorted(_SAFE_PROVIDERS))
            real_names = ", ".join(sorted(_REAL_PROVIDERS))
            raise ValueError(
                f"Provider '{resolved}' is a real provider and requires "
                f"allow_real=True. "
                f"Safe providers: {safe_names}. "
                f"Real providers (guarded): {real_names}."
            )
        return _REAL_PROVIDERS[resolved]

    safe_names = ", ".join(sorted(_SAFE_PROVIDERS))
    real_names = ", ".join(sorted(_REAL_PROVIDERS))
    raise ValueError(
        f"Unknown provider '{resolved}'. "
        f"Safe providers: {safe_names}. "
        f"Real providers (guarded, require allow_real=True): {real_names}."
    )


def route(
    execution: dict,
    provider_name: str | None = None,
    prompt_package: dict | None = None,
    allow_real: bool = False,
) -> ProviderResult:
    """Route *execution* to the requested provider and return its result.

    Args:
        execution: Execution payload dict.
        provider_name: Provider name. Defaults to 'none'.
        prompt_package: Optional prompt package passed to provider.
        allow_real: If True, real providers are accessible (but still gated
                    inside GeminiVertexProvider by the wave constant and env
                    vars). Default False — safe providers only.

    Returns:
        ProviderResult from the selected provider.

    Raises:
        ValueError: If provider name is unknown or real but allow_real=False.
    """
    provider = get_provider(provider_name, allow_real=allow_real)
    # enable_real_llm mirrors allow_real so the provider can apply its own gate.
    return provider.run(
        execution=execution,
        prompt_package=prompt_package,
        enable_real_llm=allow_real,
    )
