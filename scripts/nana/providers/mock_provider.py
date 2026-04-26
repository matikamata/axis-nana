#!/usr/bin/env python3
"""Deterministic local mock provider for AXIS NANA.

Wave 2c.3: populates traceability fields (provider_run_id, provider_run_type,
artifact_status, canonical_status, canonical_refs) to satisfy the richer
validate_provider_result.py schema.
"""

from __future__ import annotations

import hashlib
import json

from .base_provider import BaseProvider, ProviderResult


def _provider_run_id(execution_id: str, provider: str) -> str:
    """Deterministic run ID: sha256(execution_id + provider). No time, no UUID."""
    payload = json.dumps(
        {"execution_id": execution_id, "provider": provider},
        sort_keys=True,
        ensure_ascii=True,
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"provider-{digest[:16]}"


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
        execution_id = execution.get("execution_id") or "unknown"
        canonical_refs: list = (
            list(prompt_package.get("canonical_refs", []))
            if prompt_package
            else []
        )
        return ProviderResult(
            provider=self.name,
            provider_status=self.provider_status,
            provider_decision="MOCK_ONLY",
            llm_called=False,
            answer_generated=True,
            simulated_answer=(
                "[SIMULATED PLACEHOLDER \u2014 no model was called] "
                f"Concept: {concept_id}"
            ),
            # Wave 2c.3 traceability fields
            provider_run_id=_provider_run_id(execution_id, self.name),
            provider_run_type="offline_mock",
            artifact_status="DERIVATIVE_NON_CANONICAL",
            canonical_status="non_canonical",
            canonical_refs=canonical_refs,
        )
