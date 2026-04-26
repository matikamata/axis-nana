#!/usr/bin/env python3
"""Deterministic local retrieval for AXIS NANA bootstrap context packs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "metadata" / "nana" / "concept_registry.json"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "nana"


def load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def find_concept(registry: dict, concept_id: str) -> dict | None:
    for concept in registry.get("concepts", []):
        if concept.get("concept_id") == concept_id:
            return concept
    return None


def build_pack(concept: dict) -> dict:
    fingerprint = {
        "concept_id": concept["concept_id"],
        "canonical_refs": concept["canonical_refs"],
        "related_concepts": concept["related_concepts"],
        "status": concept["status"],
    }
    input_hash = hashlib.sha256(
        json.dumps(fingerprint, ensure_ascii=True, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return {
        "pack_id": f"context-pack-{concept['concept_id']}-bootstrap-v1",
        "pack_type": "canonical_context_pack",
        "concept_id": concept["concept_id"],
        "label": concept["label"],
        "source": "metadata/nana/concept_registry.json",
        "canonical_refs": concept["canonical_refs"],
        "related_concepts": concept["related_concepts"],
        "registry_status": concept["status"],
        "registry_notes": concept["notes"],
        "retrieval_mode": "registry_lookup",
        "interpretation_status": "not_interpreted",
        "llm_allowed": False,
        "input_hash": input_hash,
        "validation_status": "pending",
    }


def default_output_path(concept_id: str) -> Path:
    return DEFAULT_OUTPUT_DIR / f"context-pack-{concept_id}-bootstrap-v1.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate deterministic local AXIS NANA context packs."
    )
    parser.add_argument("--concept", required=True, help="Concept id to retrieve.")
    parser.add_argument(
        "--output",
        help="Optional output path. Defaults to outputs/nana/context-pack-<concept>-bootstrap-v1.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate deterministic output without external services.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    registry = load_registry()
    concept = find_concept(registry, args.concept)
    if concept is None:
        print(f"[retrieve] unknown concept: {args.concept}", file=sys.stderr)
        return 1

    pack = build_pack(concept)
    output_path = Path(args.output) if args.output else default_output_path(args.concept)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(pack, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    mode = "dry-run" if args.dry_run else "write"
    print(f"[retrieve:{mode}] wrote {output_path}")
    print(json.dumps(pack, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
