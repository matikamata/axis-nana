#!/usr/bin/env python3
"""Validate AXIS NANA source-bound prompt packages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate prompt package JSON files.")
    parser.add_argument("paths", nargs="+", help="Prompt package JSON files to validate.")
    return parser.parse_args()


def validate_package(path: Path) -> list[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return [f"invalid json: {exc}"]

    errors: list[str] = []

    if not payload.get("prompt_package_id"):
        errors.append("missing prompt_package_id")
    if payload.get("package_type") != "source_bound_prompt":
        errors.append("package_type must be source_bound_prompt")
    if not payload.get("concept_id"):
        errors.append("missing concept_id")
    if not payload.get("question"):
        errors.append("missing question")
    if not payload.get("context_pack_id"):
        errors.append("missing context_pack_id")

    canonical_refs = payload.get("canonical_refs")
    if not isinstance(canonical_refs, list) or not canonical_refs:
        errors.append("canonical_refs must be a non-empty list")

    if not payload.get("system_instruction"):
        errors.append("missing system_instruction")
    if not payload.get("user_prompt"):
        errors.append("missing user_prompt")

    constraints = payload.get("constraints")
    if not isinstance(constraints, list) or not constraints:
        errors.append("constraints must be a non-empty list")

    if payload.get("llm_call_status") != "not_called":
        errors.append("llm_call_status must be not_called")
    if not payload.get("input_hash"):
        errors.append("missing input_hash")

    return errors


def main() -> int:
    args = parse_args()
    has_errors = False

    for raw_path in args.paths:
        path = Path(raw_path)
        errors = validate_package(path)
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
