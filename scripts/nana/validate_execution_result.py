#!/usr/bin/env python3
"""Validate AXIS NANA safe-mode execution results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate execution result JSON files.")
    parser.add_argument("paths", nargs="+", help="Execution result JSON files to validate.")
    return parser.parse_args()


def validate_result(path: Path) -> list[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return [f"invalid json: {exc}"]

    errors: list[str] = []

    if not payload.get("execution_id"):
        errors.append("missing execution_id")
    if payload.get("execution_type") != "llm_execution_safe_mode":
        errors.append("execution_type must be llm_execution_safe_mode")
    if not payload.get("decision"):
        errors.append("missing decision")
    if not isinstance(payload.get("allowed_to_answer"), bool):
        errors.append("allowed_to_answer must be a boolean")
    if payload.get("llm_called") is not False:
        errors.append("llm_called must be false")
    if payload.get("execution_mode") != "safe_dry_run":
        errors.append("execution_mode must be safe_dry_run")
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
