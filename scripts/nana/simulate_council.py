#!/usr/bin/env python3
"""Simulate a local AXIS NANA council without calling any model."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "nana" / "council"
CANDIDATE_IDS = ["simulated_model_a", "simulated_model_b", "simulated_model_c"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulate a deterministic AXIS NANA council from an execution artifact."
    )
    parser.add_argument("--execution", required=True, help="Path to execution result JSON.")
    parser.add_argument(
        "--output",
        help="Optional output path. Defaults to outputs/nana/council/council-<concept>-bootstrap-v1.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run deterministically without external services or model execution.",
    )
    return parser.parse_args()


def load_execution(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"[council] invalid execution JSON: {exc}") from exc

    if payload.get("execution_type") != "llm_execution_safe_mode":
        raise SystemExit("[council] execution input must have execution_type llm_execution_safe_mode")
    if not payload.get("execution_id"):
        raise SystemExit("[council] execution input missing execution_id")
    if not payload.get("concept_id"):
        raise SystemExit("[council] execution input missing concept_id")
    if payload.get("llm_called") is not False:
        raise SystemExit("[council] execution input must keep llm_called false")

    return payload


def default_output_path(concept_id: str) -> Path:
    return DEFAULT_OUTPUT_DIR / f"council-{concept_id}-bootstrap-v1.json"


def simulate_candidate(candidate_id: str, canonical_refs: list[str]) -> dict:
    return {
        "candidate_id": candidate_id,
        "provider": "simulated",
        "llm_called": False,
        "answer_status": "simulated_placeholder",
        "cited_refs": list(canonical_refs),
        "external_claims_detected": False,
        "notes": "Placeholder candidate. No model was called.",
    }


def citation_agreement_score(candidates: list[dict], canonical_refs: list[str]) -> float:
    if not candidates:
        return 0.0

    required = sorted(canonical_refs)
    if not required:
        return 0.0

    agreeing = 0
    for candidate in candidates:
      cited = sorted(candidate.get("cited_refs") or [])
      if cited == required:
          agreeing += 1

    return round(agreeing / len(candidates), 4)


def consensus_status_for_bootstrap(llm_called: bool, agreement: float) -> str:
    if llm_called is False:
        return "NO_REAL_COUNCIL_YET"
    if agreement >= 0.8:
        return "CITATION_CONSENSUS"
    return "DISSENT_REVIEW_REQUIRED"


def build_council(execution: dict) -> dict:
    canonical_refs = list(execution.get("canonical_refs") or [])
    candidates = [simulate_candidate(candidate_id, canonical_refs) for candidate_id in CANDIDATE_IDS]
    agreement = citation_agreement_score(candidates, canonical_refs)
    consensus_status = consensus_status_for_bootstrap(False, agreement)

    fingerprint = {
        "execution_id": execution["execution_id"],
        "question": execution.get("question"),
        "canonical_refs": canonical_refs,
        "candidate_ids": CANDIDATE_IDS,
        "citation_agreement_score": agreement,
        "consensus_status": consensus_status,
    }
    input_hash = hashlib.sha256(
        json.dumps(fingerprint, ensure_ascii=True, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return {
        "council_id": f"council-{execution['concept_id']}-bootstrap-v1",
        "council_type": "nana_council_simulation",
        "concept_id": execution["concept_id"],
        "question": execution.get("question"),
        "execution_id": execution["execution_id"],
        "canonical_refs": canonical_refs,
        "candidate_responses": candidates,
        "citation_agreement_score": agreement,
        "consensus_status": consensus_status,
        "dissent_notes": [],
        "hallucination_risk": "not_evaluated",
        "llm_called": False,
        "input_hash": input_hash,
        "validation_status": "pending",
    }


def main() -> int:
    args = parse_args()
    execution = load_execution(Path(args.execution))
    payload = build_council(execution)

    output_path = Path(args.output) if args.output else default_output_path(payload["concept_id"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    mode = "dry-run" if args.dry_run else "write"
    print(f"[council:{mode}] wrote {output_path}")
    print(json.dumps(payload, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
