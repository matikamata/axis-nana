#!/usr/bin/env python3
"""Evaluate context sufficiency for AXIS NANA prompt packages."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "nana" / "gates"
CONFIDENCE_THRESHOLD = 0.5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate whether a context pack provides sufficient canonical support."
    )
    parser.add_argument("--context-pack", required=True, help="Path to context pack JSON.")
    parser.add_argument("--prompt-package", required=True, help="Path to prompt package JSON.")
    parser.add_argument(
        "--output",
        help="Optional output path. Defaults to outputs/nana/gates/gate-<concept>-bootstrap-v1.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run deterministically without external services.",
    )
    return parser.parse_args()


def load_json(path: Path, label: str) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"[gate] invalid {label} JSON: {exc}") from exc


def load_context_pack(path: Path) -> dict:
    payload = load_json(path, "context pack")
    if payload.get("pack_type") != "canonical_context_pack":
        raise SystemExit("[gate] context pack must have pack_type canonical_context_pack")
    if not payload.get("concept_id"):
        raise SystemExit("[gate] context pack missing concept_id")
    return payload


def load_prompt_package(path: Path) -> dict:
    payload = load_json(path, "prompt package")
    if payload.get("package_type") != "source_bound_prompt":
        raise SystemExit("[gate] prompt package must have package_type source_bound_prompt")
    if not payload.get("concept_id"):
        raise SystemExit("[gate] prompt package missing concept_id")
    if not payload.get("question"):
        raise SystemExit("[gate] prompt package missing question")
    return payload


def question_length_factor(question: str) -> float:
    # A tiny bounded proxy for how much explicit question text is available.
    return min(len(question.strip().split()) / 10.0, 1.0)


def clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    return max(min_value, min(value, max_value))


def default_output_path(concept_id: str) -> Path:
    return DEFAULT_OUTPUT_DIR / f"gate-{concept_id}-bootstrap-v1.json"


def build_gate(context_pack: dict, prompt_package: dict) -> dict:
    if context_pack["concept_id"] != prompt_package["concept_id"]:
        raise SystemExit("[gate] concept_id mismatch between context pack and prompt package")
    if context_pack["pack_id"] != prompt_package["context_pack_id"]:
        raise SystemExit("[gate] context pack id mismatch between inputs")

    canonical_refs = context_pack.get("canonical_refs") or []
    prompt_refs = prompt_package.get("canonical_refs") or []
    if canonical_refs != prompt_refs:
        raise SystemExit("[gate] canonical_refs mismatch between inputs")

    related_concepts = context_pack.get("related_concepts") or []
    ref_count = len(canonical_refs)
    related_count = len(related_concepts)
    q_factor = question_length_factor(prompt_package["question"])
    coverage_score = clamp((ref_count * 0.6) + (related_count * 0.2) + (q_factor * 0.2))

    if ref_count == 0:
        decision = "NO_CANONICAL_SUPPORT"
        decision_reason = "No canonical references were provided in the context pack."
        allowed_to_answer = False
    elif coverage_score < CONFIDENCE_THRESHOLD:
        decision = "ANSWER_PARTIAL"
        decision_reason = (
            f"Canonical support exists but coverage_score {coverage_score:.2f} is below "
            f"the threshold {CONFIDENCE_THRESHOLD:.2f}."
        )
        allowed_to_answer = False
    else:
        decision = "ANSWER_CONFIDENT"
        decision_reason = (
            f"Canonical support is sufficient because ref_count is {ref_count} and "
            f"coverage_score {coverage_score:.2f} meets the threshold {CONFIDENCE_THRESHOLD:.2f}."
        )
        allowed_to_answer = True

    fingerprint = {
        "context_pack_id": context_pack["pack_id"],
        "prompt_package_id": prompt_package["prompt_package_id"],
        "question": prompt_package["question"],
        "canonical_refs": canonical_refs,
        "related_concepts": related_concepts,
        "coverage_score": round(coverage_score, 4),
    }
    input_hash = hashlib.sha256(
        json.dumps(fingerprint, ensure_ascii=True, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return {
        "gate_id": f"gate-{context_pack['concept_id']}-bootstrap-v1",
        "gate_type": "context_sufficiency_evaluation",
        "concept_id": context_pack["concept_id"],
        "question": prompt_package["question"],
        "context_pack_id": context_pack["pack_id"],
        "prompt_package_id": prompt_package["prompt_package_id"],
        "canonical_refs": canonical_refs,
        "ref_count": ref_count,
        "related_concepts_count": related_count,
        "coverage_score": round(coverage_score, 4),
        "decision": decision,
        "decision_reason": decision_reason,
        "allowed_to_answer": allowed_to_answer,
        "llm_allowed": False,
        "input_hash": input_hash,
        "validation_status": "pending",
    }


def main() -> int:
    args = parse_args()
    context_pack = load_context_pack(Path(args.context_pack))
    prompt_package = load_prompt_package(Path(args.prompt_package))
    payload = build_gate(context_pack, prompt_package)

    output_path = Path(args.output) if args.output else default_output_path(payload["concept_id"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    mode = "dry-run" if args.dry_run else "write"
    print(f"[gate:{mode}] wrote {output_path}")
    print(json.dumps(payload, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
