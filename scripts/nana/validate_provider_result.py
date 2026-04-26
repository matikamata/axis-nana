#!/usr/bin/env python3
"""Validate AXIS NANA provider adapter results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate provider result JSON files.")
    parser.add_argument("paths", nargs="+", help="Provider result JSON files to validate.")
    return parser.parse_args()


def validate_result(path: Path) -> list[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return [f"invalid json: {exc}"]

    errors: list[str] = []

    if not payload.get("provider_run_id"):
        errors.append("missing provider_run_id")
    if payload.get("provider_run_type") != "nana_provider_adapter_run":
        errors.append("provider_run_type must be nana_provider_adapter_run")
    if not payload.get("concept_id"):
        errors.append("missing concept_id")
    if not payload.get("execution_id"):
        errors.append("missing execution_id")
    if not payload.get("provider"):
        errors.append("missing provider")
    if not payload.get("input_hash"):
        errors.append("missing input_hash")

    provider_backend = payload.get("provider_backend")
    if provider_backend is not None and not isinstance(provider_backend, str):
        errors.append("provider_backend must be null or a string")

    model_requested = payload.get("model_requested")
    if model_requested is not None and not isinstance(model_requested, str):
        errors.append("model_requested must be null or a string")
    if payload.get("provider") == "gemini":
        if not isinstance(model_requested, str) or not model_requested.strip():
            errors.append("gemini provider result must include non-empty model_requested")

    provider_error = payload.get("provider_error")
    if provider_error is not None and not isinstance(provider_error, str):
        errors.append("provider_error must be null or a string")
    if payload.get("provider") == "gemini" and payload.get("provider_status") in {
        "model_unavailable",
        "sdk_missing",
        "vertex_error",
        "api_key_error",
    }:
        if not isinstance(provider_error, str) or not provider_error.strip():
            errors.append("gemini failure result must include non-empty provider_error")

    canonical_refs = payload.get("canonical_refs")
    if not isinstance(canonical_refs, list) or not canonical_refs:
        errors.append("canonical_refs must be a non-empty list")

    provider = payload.get("provider")
    llm_called = payload.get("llm_called")
    real_providers = {"openai", "gemini"}
    if llm_called not in {True, False}:
        errors.append("llm_called must be a boolean")
    elif llm_called is True and provider not in real_providers:
        errors.append("llm_called may be true only for real providers")
    elif llm_called is False and provider in real_providers:
        if payload.get("provider_decision") not in {"BLOCKED", "BLOCKED_OR_NOT_ENABLED"}:
            errors.append("blocked real-provider result must use provider_decision BLOCKED or BLOCKED_OR_NOT_ENABLED")

    if provider in real_providers and llm_called is True:
        if payload.get("provider_status") != "real_call":
            errors.append("real provider call must use provider_status real_call")
        if payload.get("provider_decision") != "EXECUTED":
            errors.append("real provider call must use provider_decision EXECUTED")
        if not isinstance(payload.get("raw_answer"), str) or not payload.get("raw_answer").strip():
            errors.append("real provider call must include non-empty raw_answer")
        if not payload.get("answer_quality_flag"):
            errors.append("real provider call must include answer_quality_flag")
    elif provider not in real_providers and payload.get("raw_answer") not in {None, ""}:
        errors.append("non-real providers must not include raw_answer")

    if payload.get("artifact_status") != "DERIVATIVE_NON_CANONICAL":
        errors.append("artifact_status must be DERIVATIVE_NON_CANONICAL")
    if payload.get("canonical_status") != "non_canonical":
        errors.append("canonical_status must be non_canonical")

    return errors


def main() -> int:
    args = parse_args()
    has_errors = False

    for raw_path in args.paths:
        path = Path(raw_path)
        errors = validate_result(path)
        if errors:
            has_errors = True
            print(f"[FAIL] {path}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"[PASS] {path}")

    return 1 if has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
