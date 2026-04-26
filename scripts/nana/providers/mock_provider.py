#!/usr/bin/env python3
"""Deterministic local mock provider for AXIS NANA."""

from __future__ import annotations

from .base_provider import BaseProvider, ProviderResult


class MockProvider(BaseProvider):
    name = "mock"
    provider_status = "mocked"

    def run(
        self,
        execution: dict,
        prompt_package: dict | None = None,
        enable_real_llm: bool = False,
    ) -> ProviderResult:
        concept_id = execution.get("concept_id") or "unknown"
        return ProviderResult(
            provider=self.name,
            provider_status=self.provider_status,
            provider_decision="MOCK_ONLY",
            llm_called=False,
            answer_generated=True,
            simulated_answer=(
                "[SIMULATED PLACEHOLDER — no model was called] "
                f"Concept: {concept_id}"
            ),
        )
