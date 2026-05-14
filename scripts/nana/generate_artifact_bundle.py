#!/usr/bin/env python3
"""AXIS NANA — Wave 2c.5a — Artifact Bundle Scaffold Generator.

Creates a promotion-validator-compatible artifact directory structure from offline data.
THIS SCRIPT DOES NOT CALL REAL PROVIDERS OR APIS.
THIS SCRIPT DOES NOT READ CREDENTIALS.
THIS SCRIPT DOES NOT SET display_allowed: true.

Usage:
    python3 scripts/nana/generate_artifact_bundle.py \\
        --concept-id dukkha \\
        --artifact-set-id dukkha-scaffold-v1 \\
        --output-dir outputs/nana/ \\
        --dry-run
"""

import argparse
import json
import sys
from pathlib import Path

def _canonical_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=True)

def _build_manifest(concept_id: str, set_id: str) -> dict:
    return {
        "format_version": "1.0",
        "description": "Scaffolded artifact bundle",
        "artifact_set_id": set_id,
        "artifacts_by_concept": {
            concept_id: {
                "execution": f"execution/execution-{set_id}.json",
                "provider_run": f"provider_runs/provider-{set_id}.json",
                "council_eval": f"council/council-{set_id}.json",
                "answer_validation": f"answer_validation/validation-{set_id}.json"
            }
        }
    }

def _build_execution(concept_id: str, set_id: str) -> dict:
    return {
        "concept_id": concept_id,
        "execution_id": f"exec-{set_id}",
        "execution_type": "llm_execution_safe_mode",
        "execution_mode": "offline_scaffold",
        "provider": "scaffold_mock",
        "question": "Scaffold question placeholder",
        "llm_called": False,
        "allowed_to_answer": False,
        "decision": "DRY_RUN_ONLY"
    }

def _build_provider_run(concept_id: str, set_id: str) -> dict:
    return {
        "concept_id": concept_id,
        "provider": "scaffold_mock",
        "provider_run_id": f"prov-{set_id}",
        "provider_run_type": "offline_scaffold",
        "provider_status": "mocked",
        "llm_called": False,
        "answer_generated": True,
        "raw_answer": "This is a scaffold mock answer.",
        "model_requested": "mock-model",
        "artifact_status": "generated_unapproved",
        "canonical_status": "non_canonical",
        "canonical_refs": []
    }

def _build_council(concept_id: str, set_id: str) -> dict:
    return {
        "concept_id": concept_id,
        "council_run_id": f"council-{set_id}",
        "status": "mocked",
        "evaluations": [],
        "overall_decision": "PENDING"
    }

def _build_validation(concept_id: str, set_id: str) -> dict:
    return {
        "concept_id": concept_id,
        "validation_id": f"val-{set_id}",
        "status": "generated_unapproved",
        "display_allowed": False,
        "reason": "Scaffold bundle default — requires human approval",
        "artifact_status": "generated_unapproved"
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--concept-id", required=True)
    parser.add_argument("--artifact-set-id", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    concept_id = args.concept_id
    set_id = args.artifact_set_id
    out_dir = Path(args.output_dir) / set_id

    manifest = _build_manifest(concept_id, set_id)
    execution = _build_execution(concept_id, set_id)
    provider_run = _build_provider_run(concept_id, set_id)
    council = _build_council(concept_id, set_id)
    validation = _build_validation(concept_id, set_id)

    if args.dry_run:
        print(f"[DRY-RUN] Would create bundle at {out_dir}")
        print(f"[DRY-RUN] manifest.json:\n{_canonical_json(manifest)}")
        return 0

    if out_dir.exists():
        print(f"[ERROR] Output directory already exists: {out_dir}", file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True)
    (out_dir / "execution").mkdir()
    (out_dir / "provider_runs").mkdir()
    (out_dir / "council").mkdir()
    (out_dir / "answer_validation").mkdir()

    (out_dir / "manifest.json").write_text(_canonical_json(manifest), encoding="utf-8")
    (out_dir / manifest["artifacts_by_concept"][concept_id]["execution"]).write_text(_canonical_json(execution), encoding="utf-8")
    (out_dir / manifest["artifacts_by_concept"][concept_id]["provider_run"]).write_text(_canonical_json(provider_run), encoding="utf-8")
    (out_dir / manifest["artifacts_by_concept"][concept_id]["council_eval"]).write_text(_canonical_json(council), encoding="utf-8")
    (out_dir / manifest["artifacts_by_concept"][concept_id]["answer_validation"]).write_text(_canonical_json(validation), encoding="utf-8")

    print(f"[OK] Bundle scaffold generated: {out_dir}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
