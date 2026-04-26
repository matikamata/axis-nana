#!/usr/bin/env python3
"""Default provider that never calls any API or model.

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


class NoneProvider(BaseProvider):
    name = "none"
    provider_status = "not_configured"

    def run(
        self,
        execution: dict,
        prompt_package: dict | None = None,
        enable_real_llm: bool = False,
    ) -> ProviderResult:
        execution_id = execution.get("execution_id") or "unknown"
        canonical_refs: list = (
            list(prompt_package.get("canonical_refs", []))
            if prompt_package
            else []
        )
        return ProviderResult(
            provider=self.name,
            provider_status=self.provider_status,
            provider_decision="DRY_RUN_ONLY",
            llm_called=False,
            answer_generated=False,
            simulated_answer=None,
            # Wave 2c.3 traceability fields
            provider_run_id=_provider_run_id(execution_id, self.name),
            provider_run_type="offline_none",
            artifact_status="DERIVATIVE_NON_CANONICAL",
            canonical_status="non_canonical",
            canonical_refs=canonical_refs,
        )
