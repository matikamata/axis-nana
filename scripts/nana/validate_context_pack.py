#!/usr/bin/env python3
"""Validate AXIS NANA bootstrap context packs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate context pack JSON files.")
    parser.add_argument("paths", nargs="+", help="Context pack JSON files to validate.")
    return parser.parse_args()


def validate_pack(path: Path) -> list[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return [f"invalid json: {exc}"]

    errors: list[str] = []

    if not payload.get("pack_id"):
        errors.append("missing pack_id")
    if payload.get("pack_type") != "canonical_context_pack":
        errors.append("pack_type must be canonical_context_pack")
    if not payload.get("concept_id"):
        errors.append("missing concept_id")

    canonical_refs = payload.get("canonical_refs")
    if not isinstance(canonical_refs, list) or not canonical_refs:
        errors.append("canonical_refs must be a non-empty list")

    if not payload.get("retrieval_mode"):
        errors.append("missing retrieval_mode")
    if payload.get("interpretation_status") != "not_interpreted":
        errors.append("interpretation_status must be not_interpreted")
    if payload.get("llm_allowed") is not False:
        errors.append("llm_allowed must be false")
    if not payload.get("input_hash"):
        errors.append("missing input_hash")

    return errors


def main() -> int:
    args = parse_args()
    has_errors = False

    for raw_path in args.paths:
        path = Path(raw_path)
        errors = validate_pack(path)
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
