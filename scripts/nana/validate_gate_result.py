#!/usr/bin/env python3
"""Validate AXIS NANA gate evaluation results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate gate result JSON files.")
    parser.add_argument("paths", nargs="+", help="Gate result JSON files to validate.")
    return parser.parse_args()


def validate_result(path: Path) -> list[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return [f"invalid json: {exc}"]

    errors: list[str] = []

    if not payload.get("gate_id"):
        errors.append("missing gate_id")
    if payload.get("gate_type") != "context_sufficiency_evaluation":
        errors.append("gate_type must be context_sufficiency_evaluation")
    if not payload.get("concept_id"):
        errors.append("missing concept_id")
    if not payload.get("decision"):
        errors.append("missing decision")

    if not isinstance(payload.get("allowed_to_answer"), bool):
        errors.append("allowed_to_answer must be a boolean")

    canonical_refs = payload.get("canonical_refs")
    if not isinstance(canonical_refs, list):
        errors.append("canonical_refs must be a list")

    if not payload.get("input_hash"):
        errors.append("missing input_hash")

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
