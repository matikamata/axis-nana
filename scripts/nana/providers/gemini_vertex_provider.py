#!/usr/bin/env python3
"""Guarded Gemini/Vertex provider skeleton for AXIS NANA Wave 2c.5f.

THIS WAVE IMPLEMENTS THE SINGLE-CALL PATH BUT EXECUTION REQUIRES ALL GATES.

The adapter is structured, credential-aware, and fail-closed. Real calls
require satisfying ALL of the explicit runtime gates.

Activation requirements (ALL must be true simultaneously):
  1. REAL_CALLS_ENABLED_IN_THIS_WAVE must be True   (compile-time gate)
  2. enable_real_llm=True passed to run()           (caller gate)
  3. AXIS_NANA_ALLOW_REAL_LLM=1 in environment      (env gate)
  4. AXIS_NANA_ALLOW_GEMINI_VERTEX=1 in environment  (provider gate)
  5. GOOGLE_APPLICATION_CREDENTIALS is set           (credential gate)
  6. credential file path is readable                (file gate)

In Wave 2c.5f: REAL_CALLS_ENABLED_IN_THIS_WAVE = True, and the final
network execution block is implemented. Execution remains isolated and
guarded by strict environment requirements.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .base_provider import BaseProvider, ProviderResult

# ---------------------------------------------------------------------------
# Wave compile-time flag.
# ---------------------------------------------------------------------------
REAL_CALLS_ENABLED_IN_THIS_WAVE: bool = True

# ---------------------------------------------------------------------------
# Env var names — values are never hardcoded here.
# ---------------------------------------------------------------------------
ENV_ALLOW_REAL_LLM = "AXIS_NANA_ALLOW_REAL_LLM"
ENV_ALLOW_GEMINI = "AXIS_NANA_ALLOW_GEMINI_VERTEX"
ENV_GOOGLE_CREDS = "GOOGLE_APPLICATION_CREDENTIALS"

# Default model — can be overridden via AXIS_NANA_GEMINI_MODEL env var.
DEFAULT_MODEL = "gemini-2.0-flash"
ENV_MODEL_OVERRIDE = "AXIS_NANA_GEMINI_MODEL"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _provider_run_id(execution_id: str, provider: str, model: str) -> str:
    """Deterministic run ID. No time, no UUID, no ambient state."""
    payload = json.dumps(
        {"execution_id": execution_id, "model": model, "provider": provider},
        sort_keys=True,
        ensure_ascii=True,
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"provider-{digest[:16]}"


def _credential_path() -> Path | None:
    """Return the credential path from env, or None if not set."""
    raw = os.environ.get(ENV_GOOGLE_CREDS, "").strip()
    return Path(raw) if raw else None


def _blocked_result(
    execution_id: str,
    model: str,
    reason: str,
    canonical_refs: list,
) -> ProviderResult:
    """Return a structured blocked result — no LLM call, no secret contents."""
    return ProviderResult(
        provider="gemini_vertex",
        provider_status="blocked",
        provider_decision="BLOCKED_OR_NOT_ENABLED",
        llm_called=False,
        answer_generated=False,
        simulated_answer=None,
        model_requested=model,
        provider_error=reason,
        raw_answer=None,
        answer_quality_flag=None,
        provider_run_id=_provider_run_id(execution_id, "gemini_vertex", model),
        provider_run_type="real_gemini_vertex_guarded",
        artifact_status="DERIVATIVE_NON_CANONICAL",
        canonical_status="non_canonical",
        canonical_refs=canonical_refs,
    )


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------

class GeminiVertexProvider(BaseProvider):
    """Guarded Gemini/Vertex provider adapter.

    In Wave 2c.5f, the network implementation block is unlocked. However,
    all execution is strictly gated behind mandatory explicit explicit flags
    and environment configuration.
    """

    name = "gemini_vertex"
    provider_status = "guarded"

    def run(
        self,
        execution: dict,
        prompt_package: dict | None = None,
        enable_real_llm: bool = False,
    ) -> ProviderResult:
        execution_id = execution.get("execution_id") or "unknown"
        model = os.environ.get(ENV_MODEL_OVERRIDE, "").strip() or DEFAULT_MODEL
        canonical_refs: list = (
            list(prompt_package.get("canonical_refs", []))
            if prompt_package
            else []
        )

        # --- Gate 1: compile-time wave constant ---
        if not REAL_CALLS_ENABLED_IN_THIS_WAVE:
            return _blocked_result(
                execution_id=execution_id,
                model=model,
                reason="real_calls_disabled_in_current_wave",
                canonical_refs=canonical_refs,
            )

        # --- Gate 2: caller must explicitly request real LLM ---
        if not enable_real_llm:
            return _blocked_result(
                execution_id=execution_id,
                model=model,
                reason="enable_real_llm_not_set",
                canonical_refs=canonical_refs,
            )

        # --- Gate 3: env allow-real-llm flag ---
        if os.environ.get(ENV_ALLOW_REAL_LLM, "").strip() != "1":
            return _blocked_result(
                execution_id=execution_id,
                model=model,
                reason=f"{ENV_ALLOW_REAL_LLM} not set to 1",
                canonical_refs=canonical_refs,
            )

        # --- Gate 4: env allow-gemini flag ---
        if os.environ.get(ENV_ALLOW_GEMINI, "").strip() != "1":
            return _blocked_result(
                execution_id=execution_id,
                model=model,
                reason=f"{ENV_ALLOW_GEMINI} not set to 1",
                canonical_refs=canonical_refs,
            )

        # --- Gate 5: credential env var must be set ---
        cred_path = _credential_path()
        if cred_path is None:
            return _blocked_result(
                execution_id=execution_id,
                model=model,
                reason="GOOGLE_APPLICATION_CREDENTIALS not set",
                canonical_refs=canonical_refs,
            )

        # --- Gate 6: credential file must be readable ---
        if not cred_path.is_file():
            return _blocked_result(
                execution_id=execution_id,
                model=model,
                # Report path existence failure only — never print path contents.
                reason="credential_file_not_found",
                canonical_refs=canonical_refs,
            )

        # ----------------------------------------------------------------
        # All gates passed — real call path.
        # Lazy SDK import: only reached if REAL_CALLS_ENABLED_IN_THIS_WAVE
        # is True. SDK not required at module import time.
        # ----------------------------------------------------------------
        try:
            import vertexai  # noqa: PLC0415 — intentional lazy import
            from vertexai.generative_models import GenerativeModel  # noqa: PLC0415
        except ImportError:
            return _blocked_result(
                execution_id=execution_id,
                model=model,
                reason="sdk_missing: vertexai not installed",
                canonical_refs=canonical_refs,
            )

        # Real call execution
        try:
            # We initialize using implicit environment credentials to avoid printing or logging secrets.
            vertexai.init()
            gen_model = GenerativeModel(model)
            
            prompt_text = prompt_package.get("prompt", "") if prompt_package else ""
            if not prompt_text:
                return _blocked_result(
                    execution_id=execution_id,
                    model=model,
                    reason="empty_prompt",
                    canonical_refs=canonical_refs,
                )

            # Conservative, deterministic generation config.
            response = gen_model.generate_content(
                prompt_text,
                generation_config={"max_output_tokens": 1024, "temperature": 0.0}
            )
            raw_answer = response.text
            
            return ProviderResult(
                provider="gemini_vertex",
                provider_status="success",
                provider_decision="GENERATED",
                llm_called=True,
                answer_generated=True,
                simulated_answer=None,
                model_requested=model,
                provider_error=None,
                raw_answer=raw_answer,
                answer_quality_flag="raw",
                provider_run_id=_provider_run_id(execution_id, "gemini_vertex", model),
                provider_run_type="real_single_call_unapproved",
                artifact_status="generated_unapproved",
                canonical_status="non_canonical",
                canonical_refs=canonical_refs,
            )
        except Exception as e:
            # Catch all runtime execution errors and fail closed.
            # Do not log the raw stack trace containing local paths or credential details.
            return _blocked_result(
                execution_id=execution_id,
                model=model,
                reason="api_execution_failed",
                canonical_refs=canonical_refs,
            )
