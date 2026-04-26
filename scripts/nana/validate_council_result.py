#!/usr/bin/env python3
"""Validate AXIS NANA council simulation results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate council result JSON files.")
    parser.add_argument("paths", nargs="+", help="Council result JSON files to validate.")
    return parser.parse_args()


def validate_result(path: Path) -> list[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return [f"invalid json: {exc}"]

    errors: list[str] = []

    if not payload.get("council_id"):
        errors.append("missing council_id")
    if payload.get("council_type") != "nana_council_simulation":
        errors.append("council_type must be nana_council_simulation")
    if not payload.get("concept_id"):
        errors.append("missing concept_id")
    if not payload.get("execution_id"):
        errors.append("missing execution_id")

    candidates = payload.get("candidate_responses")
    if not isinstance(candidates, list) or not candidates:
        errors.append("candidate_responses must be a non-empty list")
    else:
        for candidate in candidates:
            if not isinstance(candidate, dict):
                errors.append("candidate_responses must contain objects")
                break
            if candidate.get("llm_called") is not False:
                errors.append("every candidate must keep llm_called false")
                break

    canonical_refs = payload.get("canonical_refs")
    if not isinstance(canonical_refs, list):
        errors.append("canonical_refs must be a list")

    if payload.get("llm_called") is not False:
        errors.append("top-level llm_called must be false")
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
