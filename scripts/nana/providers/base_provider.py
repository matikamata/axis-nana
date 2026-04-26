#!/usr/bin/env python3
"""Base provider interface for AXIS NANA dry-run adapters.

Wave 2c.3: ProviderResult extended with traceability fields required by
validate_provider_result.py. All new fields are optional with safe defaults
so existing mock/none providers remain valid without changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProviderResult:
    # ---- Wave 2c.1 / 2c.2 core fields (unchanged) ----
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

    # ---- Wave 2c.3 traceability fields (optional, backward-compatible) ----
    # Deterministic ID: sha256 of (execution_id + provider + model), not time/UUID.
    provider_run_id: str | None = None
    # Describes the run type for archival purposes.
    # Examples: offline_none, offline_mock, real_gemini_vertex_guarded
    provider_run_type: str | None = None
    # Derivative status — always DERIVATIVE_NON_CANONICAL for NANA outputs.
    artifact_status: str | None = None
    # Canonical status — always non_canonical for NANA outputs.
    canonical_status: str | None = None
    # Source refs extracted from prompt package; empty list when not applicable.
    canonical_refs: list = field(default_factory=list)


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
