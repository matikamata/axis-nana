#!/usr/bin/env python3
"""AXIS NANA safe-mode LLM execution wrapper — Wave 2c.3.

Produces a deterministic execution result and, optionally, delegates to a
provider via the router.

Wave 2c.3 adds --allow-real-provider flag and gemini_vertex to ALLOWED_PROVIDERS.
Real API calls remain blocked inside GeminiVertexProvider via
REAL_CALLS_ENABLED_IN_THIS_WAVE = False.

No network calls in this wave.  No API keys.  No real LLM.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve import path when run as a script from the repo root.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.nana.providers.router import DEFAULT_PROVIDER, route  # noqa: E402


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
EXECUTION_TYPE = "llm_execution_safe_mode"
EXECUTION_MODE = "safe_dry_run"
WAVE = "wave2c3"

# Safe offline providers always available; gemini_vertex is guarded —
# its wave constant blocks real calls even if selected via CLI.
ALLOWED_PROVIDERS = {"none", "mock", "gemini_vertex"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _canonical_json(obj: object) -> str:
    """Stable, sorted JSON string — safe for hashing."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def _input_hash(concept_id: str, question: str, provider: str) -> str:
    """Deterministic sha256 over the canonical input triple."""
    payload = _canonical_json(
        {"concept_id": concept_id, "provider": provider, "question": question}
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _execution_id(input_hash: str) -> str:
    """Stable execution identifier derived from the input hash."""
    return f"exec-{WAVE}-{input_hash[:16]}"


def _build_execution(concept_id: str, question: str, provider: str) -> dict:
    """Build the deterministic execution payload."""
    ih = _input_hash(concept_id, question, provider)
    return {
        "execution_id": _execution_id(ih),
        "execution_type": EXECUTION_TYPE,
        "execution_mode": EXECUTION_MODE,
        "concept_id": concept_id,
        "question": question,
        "provider": provider,
        "llm_called": False,
        "allowed_to_answer": False,
        "decision": "DRY_RUN_ONLY",
        "input_hash": ih,
        "wave": WAVE,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "AXIS NANA safe-mode execution wrapper. "
            "Produces a deterministic execution result without any LLM or network call."
        )
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--question",
        metavar="TEXT",
        help="Plain question string to wrap.",
    )
    group.add_argument(
        "--prompt-package",
        metavar="PATH",
        help="Path to a prompt package JSON file.",
    )
    parser.add_argument(
        "--concept-id",
        metavar="ID",
        default="unknown",
        help="Concept identifier (default: unknown).",
    )
    parser.add_argument(
        "--provider",
        metavar="NAME",
        default=DEFAULT_PROVIDER,
        choices=sorted(ALLOWED_PROVIDERS),
        help=f"Safe provider to use: {sorted(ALLOWED_PROVIDERS)} (default: {DEFAULT_PROVIDER}).",
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        help="Write execution result JSON to this path (file must not exist unless --overwrite).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting an existing output file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print result to stdout only; do not write to --output.",
    )
    parser.add_argument(
        "--run-provider",
        action="store_true",
        help=(
            "After building the execution record, call the selected provider "
            "and include its result in the output."
        ),
    )
    parser.add_argument(
        "--allow-real-provider",
        action="store_true",
        default=False,
        help=(
            "Pass allow_real=True to the router, enabling real provider routing. "
            "In Wave 2c.3 real API calls remain blocked inside the provider itself "
            "(REAL_CALLS_ENABLED_IN_THIS_WAVE=False). "
            "Requires --run-provider."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    # --- resolve question and optional prompt_package ---
    prompt_package: dict | None = None
    if args.question:
        question = args.question
    else:
        pp_path = Path(args.prompt_package)
        if not pp_path.is_file():
            print(f"[ERROR] prompt-package file not found: {pp_path}", file=sys.stderr)
            return 1
        try:
            prompt_package = json.loads(pp_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            print(f"[ERROR] could not read prompt-package: {exc}", file=sys.stderr)
            return 1
        question = str(prompt_package.get("question", ""))

    provider_name: str = args.provider

    # --- build deterministic execution record ---
    execution = _build_execution(
        concept_id=args.concept_id,
        question=question,
        provider=provider_name,
    )

    # --- optionally call provider ---
    output_doc: dict = {"execution_result": execution}
    if args.run_provider:
        allow_real: bool = getattr(args, "allow_real_provider", False)
        try:
            provider_result = route(
                execution=execution,
                provider_name=provider_name,
                prompt_package=prompt_package,
                allow_real=allow_real,
            )
        except ValueError as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 1
        output_doc["provider_result"] = asdict(provider_result)

    result_json = _canonical_json(output_doc)

    # --- output ---
    if args.dry_run or not args.output:
        print(result_json)
        return 0

    out_path = Path(args.output)
    if out_path.exists() and not args.overwrite:
        print(
            f"[ERROR] output file already exists: {out_path}  "
            "(use --overwrite to replace)",
            file=sys.stderr,
        )
        return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(result_json, encoding="utf-8")
    print(f"[OK] written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
