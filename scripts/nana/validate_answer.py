#!/usr/bin/env python3
"""Validate provider answers before any derivative display in AXIS NANA."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "nana" / "answer_validation"
REF_PATTERN = re.compile(r"\b[A-Z]{2}\.[A-Z]{2}\.[0-9]{3}\b")
CANONICAL_AUTHORITY_PATTERN = re.compile(
    r"\b(canonical authority|this is canon|this is canonical|authoritative canon|equal to canon)\b",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate provider answers for AXIS NANA.")
    parser.add_argument("--provider-run", required=True, help="Provider run JSON path.")
    parser.add_argument("--prompt-package", required=True, help="Prompt package JSON path.")
    parser.add_argument("--gate", required=True, help="Gate JSON path.")
    parser.add_argument("--output", help="Optional output JSON path.")
    parser.add_argument("--dry-run", action="store_true", help="Run validation without changing behavior.")
    return parser.parse_args()


def load_json(path: Path, expected_key: str, expected_value: str) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"[answer-validator] invalid JSON in {path}: {exc}") from exc

    if payload.get(expected_key) != expected_value:
        raise SystemExit(
            f"[answer-validator] {path} must contain {expected_key}={expected_value}"
        )
    return payload


def default_output_path(provider_run: dict) -> Path:
    provider_run_id = str(provider_run.get("provider_run_id") or "provider-unknown-bootstrap-v1")
    suffix = provider_run_id.removeprefix("provider-")
    return DEFAULT_OUTPUT_DIR / f"answer-validation-{suffix}.json"


def normalize_refs(refs: list[str] | None) -> list[str]:
    seen: dict[str, bool] = {}
    for ref in refs or []:
        normalized = str(ref or "").strip().upper()
        if normalized:
            seen[normalized] = True
    return list(seen.keys())


def extract_refs(text: str) -> list[str]:
    return normalize_refs(REF_PATTERN.findall(text or ""))


def has_sources_section(text: str) -> bool:
    return bool(re.search(r"(^|\n)\s*Sources:\s*", text or "", flags=re.IGNORECASE))


def claims_canonical_authority(text: str) -> bool:
    return bool(CANONICAL_AUTHORITY_PATTERN.search(text or ""))


def build_checks(
    *,
    has_raw_answer: bool,
    has_sources: bool,
    refs_within_allowed_set: bool,
    claims_authority: bool,
    marked_derivative: bool,
    quality_unverified: bool,
) -> dict:
    return {
        "has_raw_answer": has_raw_answer,
        "has_sources_section": has_sources,
        "refs_within_allowed_set": refs_within_allowed_set,
        "claims_canonical_authority": claims_authority,
        "marked_derivative": marked_derivative,
        "quality_unverified": quality_unverified,
    }


def build_result(
    provider_run: dict,
    prompt_package: dict,
    gate: dict,
    status: str,
    display_allowed: bool,
    canonical_refs_found: list[str],
    unknown_refs_found: list[str],
    checks: dict,
) -> dict:
    fingerprint = {
        "provider_run_id": provider_run.get("provider_run_id"),
        "prompt_package_id": prompt_package.get("prompt_package_id"),
        "gate_id": gate.get("gate_id"),
        "answer_validation_status": status,
        "canonical_refs_found": canonical_refs_found,
        "unknown_refs_found": unknown_refs_found,
    }
    input_hash = hashlib.sha256(
        json.dumps(fingerprint, ensure_ascii=True, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return {
        "answer_validation_id": "answer-validation-"
        + str(provider_run.get("provider_run_id") or "unknown").removeprefix("provider-"),
        "validation_type": "nana_answer_validation",
        "provider_run_id": provider_run.get("provider_run_id"),
        "concept_id": provider_run.get("concept_id"),
        "llm_called": provider_run.get("llm_called") is True,
        "gate_decision": gate.get("decision"),
        "answer_validation_status": status,
        "display_allowed": display_allowed,
        "canonical_refs_allowed": normalize_refs(prompt_package.get("canonical_refs")),
        "canonical_refs_found": canonical_refs_found,
        "unknown_refs_found": unknown_refs_found,
        "checks": checks,
        "input_hash": input_hash,
        "validation_status": "pending",
    }


def validate_answer(provider_run: dict, prompt_package: dict, gate: dict) -> dict:
    allowed_refs = normalize_refs(prompt_package.get("canonical_refs"))
    raw_answer = str(provider_run.get("raw_answer") or "").strip()
    refs_found = extract_refs(raw_answer)
    unknown_refs = [ref for ref in refs_found if ref not in allowed_refs]
    approved_refs_found = [ref for ref in refs_found if ref in allowed_refs]
    derivative_marked = (
        provider_run.get("artifact_status") == "DERIVATIVE_NON_CANONICAL"
        and provider_run.get("canonical_status") == "non_canonical"
    )
    quality_unverified = provider_run.get("answer_quality_flag") == "UNVERIFIED"
    sources_present = has_sources_section(raw_answer)
    canonical_authority_claim = claims_canonical_authority(raw_answer)

    if provider_run.get("llm_called") is not True:
        return build_result(
            provider_run,
            prompt_package,
            gate,
            "NOT_APPLICABLE_NO_LLM_CALL",
            False,
            [],
            [],
            build_checks(
                has_raw_answer=False,
                has_sources=False,
                refs_within_allowed_set=True,
                claims_authority=False,
                marked_derivative=derivative_marked,
                quality_unverified=quality_unverified or provider_run.get("answer_quality_flag") is None,
            ),
        )

    if gate.get("allowed_to_answer") is not True:
        return build_result(
            provider_run,
            prompt_package,
            gate,
            "REJECTED_GATE_BLOCKED",
            False,
            approved_refs_found,
            unknown_refs,
            build_checks(
                has_raw_answer=bool(raw_answer),
                has_sources=sources_present,
                refs_within_allowed_set=not unknown_refs,
                claims_authority=canonical_authority_claim,
                marked_derivative=derivative_marked,
                quality_unverified=quality_unverified,
            ),
        )

    if not raw_answer:
        return build_result(
            provider_run,
            prompt_package,
            gate,
            "REJECTED_EMPTY_ANSWER",
            False,
            [],
            [],
            build_checks(
                has_raw_answer=False,
                has_sources=False,
                refs_within_allowed_set=True,
                claims_authority=False,
                marked_derivative=derivative_marked,
                quality_unverified=quality_unverified,
            ),
        )

    if not sources_present or not approved_refs_found:
        return build_result(
            provider_run,
            prompt_package,
            gate,
            "REJECTED_NO_SOURCES",
            False,
            approved_refs_found,
            unknown_refs,
            build_checks(
                has_raw_answer=True,
                has_sources=sources_present,
                refs_within_allowed_set=not unknown_refs,
                claims_authority=canonical_authority_claim,
                marked_derivative=derivative_marked,
                quality_unverified=quality_unverified,
            ),
        )

    if unknown_refs:
        return build_result(
            provider_run,
            prompt_package,
            gate,
            "REJECTED_UNKNOWN_REF",
            False,
            approved_refs_found,
            unknown_refs,
            build_checks(
                has_raw_answer=True,
                has_sources=sources_present,
                refs_within_allowed_set=False,
                claims_authority=canonical_authority_claim,
                marked_derivative=derivative_marked,
                quality_unverified=quality_unverified,
            ),
        )

    if canonical_authority_claim:
        return build_result(
            provider_run,
            prompt_package,
            gate,
            "REJECTED_CANONICAL_AUTHORITY_CLAIM",
            False,
            approved_refs_found,
            [],
            build_checks(
                has_raw_answer=True,
                has_sources=sources_present,
                refs_within_allowed_set=True,
                claims_authority=True,
                marked_derivative=derivative_marked,
                quality_unverified=quality_unverified,
            ),
        )

    if not derivative_marked:
        return build_result(
            provider_run,
            prompt_package,
            gate,
            "REJECTED_NOT_MARKED_DERIVATIVE",
            False,
            approved_refs_found,
            [],
            build_checks(
                has_raw_answer=True,
                has_sources=sources_present,
                refs_within_allowed_set=True,
                claims_authority=False,
                marked_derivative=False,
                quality_unverified=quality_unverified,
            ),
        )

    if not quality_unverified:
        return build_result(
            provider_run,
            prompt_package,
            gate,
            "REJECTED_NOT_UNVERIFIED",
            False,
            approved_refs_found,
            [],
            build_checks(
                has_raw_answer=True,
                has_sources=sources_present,
                refs_within_allowed_set=True,
                claims_authority=False,
                marked_derivative=True,
                quality_unverified=False,
            ),
        )

    return build_result(
        provider_run,
        prompt_package,
        gate,
        "DISPLAY_ALLOWED_DERIVATIVE",
        True,
        approved_refs_found,
        [],
        build_checks(
            has_raw_answer=True,
            has_sources=True,
            refs_within_allowed_set=True,
            claims_authority=False,
            marked_derivative=True,
            quality_unverified=True,
        ),
    )


def main() -> int:
    args = parse_args()
    provider_run = load_json(Path(args.provider_run), "provider_run_type", "nana_provider_adapter_run")
    prompt_package = load_json(Path(args.prompt_package), "package_type", "source_bound_prompt")
    gate = load_json(Path(args.gate), "gate_type", "context_sufficiency_evaluation")

    result = validate_answer(provider_run, prompt_package, gate)
    output_path = Path(args.output) if args.output else default_output_path(provider_run)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    mode = "dry-run" if args.dry_run else "write"
    print(f"[answer-validator:{mode}] wrote {output_path}")
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
