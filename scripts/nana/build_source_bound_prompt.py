#!/usr/bin/env python3
"""Build deterministic source-bound prompt packages from context packs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "nana" / "prompts"

SYSTEM_INSTRUCTION = (
    "You are AXIS NANA operating in source-bound mode.\n"
    "Use only the canonical references provided in this prompt package.\n"
    "Do not use external knowledge.\n"
    "Do not speculate.\n"
    "Every factual claim must cite at least one canonical reference.\n"
    "You MUST include a dedicated final section titled exactly:\n"
    "Sources:\n"
    "Under that section, list only canonical references from the provided canonical_refs list.\n"
    "Do not invent or add any references outside that list.\n"
    "Inline citations are allowed but are not sufficient. A final Sources: section is mandatory.\n"
    'If the provided context is insufficient, answer: "Insufficient canonical context."'
)

CONSTRAINTS = [
    "Use only the canonical context provided.",
    "Cite every claim with canonical refs.",
    "Do not introduce external interpretation.",
    "Include a dedicated final Sources: section listing only provided canonical refs.",
    "Inline citations alone are not sufficient; a final Sources: section is mandatory.",
    "If context is insufficient, say insufficient.",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build deterministic source-bound prompt packages."
    )
    parser.add_argument("--context-pack", required=True, help="Path to context pack JSON.")
    parser.add_argument("--question", required=True, help="Question to bind to the prompt.")
    parser.add_argument(
        "--output",
        help="Optional output path. Defaults to outputs/nana/prompts/prompt-<concept>-bootstrap-v1.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build the prompt package without external services.",
    )
    return parser.parse_args()


def load_context_pack(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"[prompt_builder] invalid context pack JSON: {exc}") from exc

    if payload.get("pack_type") != "canonical_context_pack":
        raise SystemExit("[prompt_builder] input must have pack_type canonical_context_pack")
    if not payload.get("canonical_refs"):
        raise SystemExit("[prompt_builder] input must contain non-empty canonical_refs")
    if not payload.get("concept_id"):
        raise SystemExit("[prompt_builder] input must contain concept_id")

    return payload


def build_user_prompt(context_pack: dict, question: str) -> str:
    related = context_pack.get("related_concepts") or []
    related_text = ", ".join(related) if related else "None"
    refs_text = ", ".join(context_pack["canonical_refs"])

    return (
        "Question:\n"
        f"{question}\n\n"
        "Concept ID:\n"
        f"{context_pack['concept_id']}\n\n"
        "Context Pack ID:\n"
        f"{context_pack['pack_id']}\n\n"
        "Canonical References:\n"
        f"{refs_text}\n\n"
        "Related Concepts:\n"
        f"{related_text}\n\n"
        "Instructions:\n"
        "- Use only the canonical context listed above.\n"
        "- Cite every claim with canonical refs.\n"
        "- Do not introduce external interpretation.\n"
        "- You MUST include a dedicated final section titled exactly: Sources:\n"
        "- Under that section, list only canonical references from the provided canonical_refs list.\n"
        "- Do not invent or add any references outside that list.\n"
        "- Inline citations are allowed but are not sufficient. A final Sources: section is mandatory.\n"
        '- If context is insufficient, answer exactly: "Insufficient canonical context."'
    )


def build_prompt_package(context_pack: dict, question: str) -> dict:
    concept_id = context_pack["concept_id"]
    fingerprint = {
        "context_pack_id": context_pack["pack_id"],
        "question": question,
        "canonical_refs": context_pack["canonical_refs"],
        "related_concepts": context_pack.get("related_concepts", []),
        "constraints": CONSTRAINTS,
    }
    input_hash = hashlib.sha256(
        json.dumps(fingerprint, ensure_ascii=True, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return {
        "prompt_package_id": f"prompt-{concept_id}-bootstrap-v1",
        "package_type": "source_bound_prompt",
        "concept_id": concept_id,
        "question": question,
        "context_pack_id": context_pack["pack_id"],
        "canonical_refs": context_pack["canonical_refs"],
        "system_instruction": SYSTEM_INSTRUCTION,
        "user_prompt": build_user_prompt(context_pack, question),
        "constraints": CONSTRAINTS,
        "llm_call_status": "not_called",
        "input_hash": input_hash,
        "validation_status": "pending",
    }


def default_output_path(concept_id: str) -> Path:
    return DEFAULT_OUTPUT_DIR / f"prompt-{concept_id}-bootstrap-v1.json"


def main() -> int:
    args = parse_args()
    context_pack_path = Path(args.context_pack)
    context_pack = load_context_pack(context_pack_path)
    payload = build_prompt_package(context_pack, args.question)

    output_path = Path(args.output) if args.output else default_output_path(payload["concept_id"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    mode = "dry-run" if args.dry_run else "write"
    print(f"[prompt_builder:{mode}] wrote {output_path}")
    print(json.dumps(payload, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
