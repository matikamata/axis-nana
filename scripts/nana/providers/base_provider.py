#!/usr/bin/env python3
"""Base provider interface for AXIS NANA dry-run adapters."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProviderResult:
    provider: str
    provider_status: str
    provider_decision: str
    llm_called: bool
    answer_generated: bool
    simulated_answer: str | None
    provider_backend: str | None = None
    model_requested: str | None = None
    provider_error: str | None = None
    raw_answer: str | None = None
    answer_quality_flag: str | None = None


class BaseProvider:
    name = "base"
    provider_status = "unknown"

    def run(  # pragma: no cover - interface only
        self,
        execution: dict,
        prompt_package: dict | None = None,
        enable_real_llm: bool = False,
    ) -> ProviderResult:
        raise NotImplementedError
