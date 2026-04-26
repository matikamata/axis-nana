#!/usr/bin/env python3
"""Default provider that never calls any API or model."""

from __future__ import annotations

from .base_provider import BaseProvider, ProviderResult


class NoneProvider(BaseProvider):
    name = "none"
    provider_status = "not_configured"

    def run(
        self,
        execution: dict,
        prompt_package: dict | None = None,
        enable_real_llm: bool = False,
    ) -> ProviderResult:
        return ProviderResult(
            provider=self.name,
            provider_status=self.provider_status,
            provider_decision="DRY_RUN_ONLY",
            llm_called=False,
            answer_generated=False,
            simulated_answer=None,
        )
